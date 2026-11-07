/* SPDX-License-Identifier: GPL-2.0-or-later */
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <stdarg.h>
#include <sys/time.h>
#include <dvdnav/dvdnav.h>
#include "vm/decoder.h"
#include "vm/vm.h"
#include "vm/vmcmd.h"
#include "vm/getset.h"
#include "dvdnav_internal.h"
#include "fingerprint.h"

static unsigned sequence;
static uint16_t previous_g[16],previous_s[24];
static const char *domain(DVDDomain_t d) {
    switch(d) { case DVD_DOMAIN_FirstPlay:return "first-play";case DVD_DOMAIN_VMGM:return "vmg-menu";
        case DVD_DOMAIN_VTSMenu:return "vts-menu";case DVD_DOMAIN_VTSTitle:return "title";default:return "unknown"; }
}
static const char *event_name(int e) {
    switch(e) {case DVDNAV_STILL_FRAME:return "STILL_FRAME";case DVDNAV_WAIT:return "WAIT";
        case DVDNAV_CELL_CHANGE:return "CELL_CHANGE";case DVDNAV_VTS_CHANGE:return "VTS_CHANGE";
        case DVDNAV_NAV_PACKET:return "NAV_PACKET";case DVDNAV_STOP:return "STOP";
        case DVDNAV_HIGHLIGHT:return "HIGHLIGHT";case DVDNAV_HOP_CHANNEL:return "HOP_CHANNEL";
        case DVDNAV_SPU_CLUT_CHANGE:return "SPU_CLUT_CHANGE";case DVDNAV_SPU_STREAM_CHANGE:return "SPU_STREAM_CHANGE";
        case DVDNAV_AUDIO_STREAM_CHANGE:return "AUDIO_STREAM_CHANGE";default:return "OTHER";}
}
static void log_callback(void *p,dvdnav_logger_level_t l,const char *fmt,va_list args) {
    (void)p;if(l==DVDNAV_LOGGER_LEVEL_WARN || l==DVDNAV_LOGGER_LEVEL_ERROR) { vfprintf(stderr,fmt,args);fputc('\n',stderr); }
}
static int source_language(vm_t *vm) {
    if(vm->state.domain==DVD_DOMAIN_VTSTitle || vm->state.domain==DVD_DOMAIN_FirstPlay) return 0;
    ifo_handle_t *ifo=vm->state.domain==DVD_DOMAIN_VMGM ? vm->vmgi : vm->vtsi;
    if(!ifo || !ifo->pgci_ut) return -1;
    /* Use the VM's actual chosen table, including its language fallback. */
    const pgcit_t *selected=get_PGCIT(vm);
    for(unsigned i=0;i<ifo->pgci_ut->nr_of_lus;i++)
        if(ifo->pgci_ut->lu[i].pgcit==selected) return ifo->pgci_ut->lu[i].lang_code;
    return -1;
}
static void snapshot(dvdnav_t *nav,const char *input,const char *event,int ok,int still,const char *fp) {
    dvd_state_t *s=&nav->vm->state;registers_t *r=&s->registers;
    int vts=(s->domain==DVD_DOMAIN_VMGM || s->domain==DVD_DOMAIN_FirstPlay) ? 0 : s->vtsN;
    int pgc=s->domain==DVD_DOMAIN_FirstPlay ? 0 : s->pgcN;
    printf("{\"schemaVersion\":1,\"sourceFingerprint\":\"%s\",\"sequence\":%u,\"input\":\"%s\",\"event\":\"%s\",\"ok\":%s,\"vts\":%d,\"rawVts\":%d,\"language\":%d,\"domain\":\"%s\",\"pgc\":%d,\"program\":%d,\"cell\":%d,\"block\":%d,\"navSector\":%u,\"mediaTicks\":%lld,\"buttons\":%u,\"stillSeconds\":%d,\"registers\":{\"gprm\":[",
        fp,sequence++,input,event,ok?"true":"false",vts,s->vtsN,source_language(nav->vm),domain(s->domain),pgc,s->pgN,s->cellN,s->blockN,
        nav->pci.pci_gi.nv_pck_lbn,(long long)dvdnav_get_current_time(nav),nav->pci.hli.hl_gi.btn_ns,still);
    for(int i=0;i<16;i++) printf("%s%u",i?",":"",r->GPRM[i]);
    printf("],\"sprm\":[");for(int i=0;i<24;i++) printf("%s%u",i?",":"",r->SPRM[i]);
    printf("],\"gprmMode\":[");for(int i=0;i<16;i++) printf("%s%u",i?",":"",r->GPRM_mode[i]);
    printf("],\"counterEpoch\":[");for(int i=0;i<16;i++) printf("%s[%lld,%lld]",i?",":"",(long long)r->GPRM_time[i].tv_sec,(long long)r->GPRM_time[i].tv_usec);
    printf("]},\"registerDelta\":[");int first=1;
    for(int bank=0;bank<2;bank++) for(int i=0;i<(bank?24:16);i++) {
        uint16_t *values=bank?r->SPRM:r->GPRM,*old=bank?previous_s:previous_g;
        if(values[i]!=old[i]) {
            printf("%s{\"bank\":\"%s\",\"index\":%d,\"before\":%u,\"after\":%u}",first?"":",",bank?"sprm":"gprm",i,old[i],values[i]);first=0;
        }
        old[i]=values[i];
    }
    printf("]}\n");fflush(stdout);
}
static int disassemble(void) {
    char line[128];
    while(fgets(line,sizeof(line),stdin)) {
        line[strcspn(line,"\r\n")]=0;if(strlen(line)!=16) return 1;
        vm_cmd_t cmd;
        for(int i=0;i<8;i++) { unsigned byte;if(sscanf(line+2*i,"%2x",&byte)!=1) return 1;cmd.bytes[i]=(uint8_t)byte; }
        fprintf(stderr,"%s\t",line);vm_print_mnemonic(&cmd);fputc('\n',stderr);
    }
    return 0;
}
int main(int argc,char **argv) {
    if(argc==2 && !strcmp(argv[1],"--disassemble")) return disassemble();
    if(argc!=2 && argc!=4) {fprintf(stderr,"Usage: trace_game VIDEO_TS [--seed integer]\n");return 2;}
    unsigned seed=1;if(argc==4) { if(strcmp(argv[2],"--seed")) return 2;seed=(unsigned)strtoul(argv[3],NULL,10); }
    dvdnav_t *nav=NULL;dvdnav_logger_cb logger={log_callback};
    if(dvdnav_open2(&nav,NULL,&logger,argv[1])!=DVDNAV_STATUS_OK) return 1;
    dvdnav_set_readahead_flag(nav,0);srand(seed);
    char fp[65];unsigned count=nav->vm->vmgi->vmgi_mat->vmg_nr_of_title_sets;
    if(!fingerprint(argv[1],count,fp)) {dvdnav_close(nav);return 1;}
    printf("{\"schemaVersion\":1,\"event\":\"header\",\"sourceFingerprint\":\"%s\",\"seed\":%u,\"clock\":\"uncontrolled wall clock; manual media stepping and explicit still/wait advance\",\"registerSemantics\":\"raw register bases; counter modes and epochs included\",\"libdvdnav\":\"7.0.0 compiled with tracer\"}\n",fp,seed);fflush(stdout);
    char line[128];int failed=0;
    while(fgets(line,sizeof(line),stdin)) {
        line[strcspn(line,"\r\n")]=0;if(!strcmp(line,"quit")) break;
        int ok=1,still=-1,event=-1;const char *action=NULL;unsigned char block[2048];
        if(!strcmp(line,"next")) {
            action="next";int32_t length=0,e=0;unsigned loops=0;
            do {ok=dvdnav_get_next_block(nav,block,&e,&length)==DVDNAV_STATUS_OK;loops++;}
            while(ok && (e==DVDNAV_BLOCK_OK || e==DVDNAV_NOP) && loops<100000);
            if(loops>=100000) ok=0;
            event=e;if(e==DVDNAV_STILL_FRAME) still=((dvdnav_still_event_t *)block)->length;
        } else if(!strcmp(line,"activate")) {action="activate";ok=dvdnav_button_activate(nav,dvdnav_get_current_nav_pci(nav))==DVDNAV_STATUS_OK;
        } else if(!strcmp(line,"advance-still")) {action="advance-still";ok=dvdnav_still_skip(nav)==DVDNAV_STATUS_OK;
        } else if(!strcmp(line,"advance-wait")) {action="advance-wait";ok=dvdnav_wait_skip(nav)==DVDNAV_STATUS_OK;
        } else {
            int button;char extra;
            if(sscanf(line,"select %d %c",&button,&extra)==1 && button>=1 && button<=36) {
                action="select";ok=dvdnav_button_select(nav,dvdnav_get_current_nav_pci(nav),button)==DVDNAV_STATUS_OK;
            } else {fprintf(stderr,"Unknown input: %s\n",line);failed=1;break;}
        }
        snapshot(nav,!strcmp(action,"select")?line:action,event<0?"INPUT":event_name(event),ok,still,fp);
        if(!ok) {
            fprintf(stderr,"%s; VOBU start=%d next=%d block=%d length=%d\n",dvdnav_err_to_string(nav),
                    nav->vobu.vobu_start,nav->vobu.vobu_next,nav->vobu.blockN,nav->vobu.vobu_length);
            failed=1;break;
        }
        if(event==DVDNAV_STOP) break;
    }
    dvdnav_close(nav);return failed;
}
