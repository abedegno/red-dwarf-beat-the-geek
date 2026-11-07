/* SPDX-License-Identifier: GPL-2.0-or-later */
#include <stdio.h>
#include <stdlib.h>
#include <stdarg.h>
#include <dvdread/dvd_reader.h>
#include <dvdread/ifo_read.h>
#include "fingerprint.h"

static void logger(void *p, dvd_logger_level_t level, const char *fmt, va_list args) {
    (void)p;
    if (level == DVD_LOGGER_LEVEL_ERROR || level == DVD_LOGGER_LEVEL_WARN) {
        vfprintf(stderr, fmt, args); fputc('\n', stderr);
    }
}
static int bcd(unsigned x) { return (int)((x >> 4) * 10 + (x & 15)); }
static double seconds(dvd_time_t t) {
    double fps = (t.frame_u >> 6) == 1 ? 25.0 : 30000.0 / 1001;
    return bcd(t.hour)*3600 + bcd(t.minute)*60 + bcd(t.second) + bcd(t.frame_u & 63)/fps;
}
static void commands(vm_cmd_t *cmd, unsigned count) {
    putchar('[');
    for (unsigned i=0; i<count; i++) {
        if (i) putchar(',');
        putchar('"');
        for (unsigned j=0; j<8; j++) printf("%02x", cmd[i].bytes[j]);
        putchar('"');
    }
    putchar(']');
}
static void display(video_attr_t v) {
    printf("{\"aspect\":\"%s\",\"aspectCode\":%u,\"videoFormat\":%u,\"pictureSize\":%u,\"permittedDisplayFormats\":%u}",
        v.display_aspect_ratio==0 ? "4:3" : v.display_aspect_ratio==3 ? "16:9" : "reserved",
        v.display_aspect_ratio, v.video_format, v.picture_size, v.permitted_df);
}
static void pgc(pgc_t *p, int vts, const char *domain, int num, int lang, int entry, video_attr_t v) {
    printf("{\"vts\":%d,\"domain\":\"%s\",\"pgc\":%d,\"language\":%d,\"entryId\":%d,\"display\":", vts,domain,num,lang,entry);
    display(v);
    printf(",\"duration\":%.6f,\"stillTime\":%u,\"playbackMode\":%u,\"nextPgc\":%u,\"previousPgc\":%u,\"goUpPgc\":%u,\"palette\":[",
        seconds(p->playback_time),p->still_time,p->pg_playback_mode,p->next_pgc_nr,p->prev_pgc_nr,p->goup_pgc_nr);
    for (int i=0;i<16;i++) printf("%s%u",i?",":"",p->palette[i]);
    printf("],\"audioControl\":[");
    for (int i=0;i<8;i++) printf("%s%u",i?",":"",p->audio_control[i]);
    printf("],\"subpictureControl\":[");
    for (int i=0;i<32;i++) printf("%s%u",i?",":"",p->subp_control[i]);
    printf("],\"programs\":[");
    for (unsigned i=0;i<p->nr_of_programs;i++) printf("%s%u",i?",":"",p->program_map[i]);
    printf("],\"cells\":[");
    for (unsigned i=0;i<p->nr_of_cells;i++) {
        cell_playback_t c=p->cell_playback[i]; cell_position_t pos=p->cell_position[i];
        printf("%s{\"cell\":%u,\"vobId\":%u,\"cellId\":%u,\"firstSector\":%u,\"lastSector\":%u,\"firstIlvuEnd\":%u,\"lastVobuStart\":%u,\"duration\":%.6f,\"stillTime\":%u,\"commandNumber\":%u,\"blockMode\":%u,\"blockType\":%u,\"interleaved\":%u,\"discontinuity\":%u}",
            i?",":"",i+1,pos.vob_id_nr,pos.cell_nr,c.first_sector,c.last_sector,c.first_ilvu_end_sector,c.last_vobu_start_sector,
            seconds(c.playback_time),c.still_time,c.cell_cmd_nr,c.block_mode,c.block_type,c.interleaved,c.stc_discontinuity);
    }
    pgc_command_tbl_t *c=p->command_tbl;
    printf("],\"commands\":{\"pre\":"); commands(c?c->pre_cmds:NULL,c?c->nr_of_pre:0);
    printf(",\"post\":"); commands(c?c->post_cmds:NULL,c?c->nr_of_post:0);
    printf(",\"cell\":"); commands(c?c->cell_cmds:NULL,c?c->nr_of_cell:0);
    printf("}}");
}
static void audio(audio_attr_t *a, int n) {
    putchar('[');
    for(int i=0;i<n;i++) printf("%s{\"index\":%d,\"format\":%u,\"channels\":%u,\"language\":%u,\"codeExtension\":%u}",
        i?",":"",i,a[i].audio_format,a[i].channels+1,a[i].lang_code,a[i].code_extension);
    putchar(']');
}
static void subp(subp_attr_t *a, int n) {
    putchar('[');
    for(int i=0;i<n;i++) printf("%s{\"index\":%d,\"type\":%u,\"language\":%u,\"codeExtension\":%u}",
        i?",":"",i,a[i].type,a[i].lang_code,a[i].code_extension);
    putchar(']');
}
int main(int argc, char **argv) {
    if(argc!=2) { fprintf(stderr,"Usage: inspect_ifo VIDEO_TS\n"); return 2; }
    dvd_logger_cb cb={logger}; dvd_reader_t *dvd=DVDOpen2(NULL,&cb,argv[1]);
    if(!dvd) return 1;
    ifo_handle_t *ifo[100]={0}; ifo[0]=ifoOpen(dvd,0);
    if(!ifo[0] || !ifo[0]->vmgi_mat) { DVDClose(dvd); return 1; }
    unsigned count=ifo[0]->vmgi_mat->vmg_nr_of_title_sets;
    if(count>99) { fprintf(stderr,"Too many title sets\n"); return 1; }
    for(unsigned i=1;i<=count;i++) {
        ifo[i]=ifoOpen(dvd,(int)i);
        if(!ifo[i] || !ifo[i]->vtsi_mat || !ifo[i]->vts_pgcit) {
            fprintf(stderr,"Cannot parse title set %u\n",i); return 1;
        }
    }
    char fp[65];if(!fingerprint(argv[1],count,fp)) { fprintf(stderr,"Cannot fingerprint IFO files\n");return 1; }
    printf("{\"schemaVersion\":1,\"sourceFingerprint\":\"%s\",\"titleSetCount\":%u,\"titles\":[",fp,count);
    tt_srpt_t *tt=ifo[0]->tt_srpt;
    for(unsigned i=0;tt && i<tt->nr_of_srpts;i++) {
        title_info_t t=tt->title[i];
        printf("%s{\"title\":%u,\"vts\":%u,\"vtsTitle\":%u,\"chapters\":%u,\"angles\":%u}",
            i?",":"",i+1,t.title_set_nr,t.vts_ttn,t.nr_of_ptts,t.nr_of_angles);
    }
    printf("],\"streams\":[");
    for(unsigned i=0;i<=count;i++) {
        if(i) putchar(',');
        printf("{\"vts\":%u,\"menuAudio\":",i);
        if(i==0) {
            vmgi_mat_t *m=ifo[0]->vmgi_mat;
            audio(&m->vmgm_audio_attr,m->nr_of_vmgm_audio_streams);
            printf(",\"menuSubpictures\":");subp(&m->vmgm_subp_attr,m->nr_of_vmgm_subp_streams);
        } else {
            vtsi_mat_t *m=ifo[i]->vtsi_mat;
            audio(&m->vtsm_audio_attr,m->nr_of_vtsm_audio_streams);
            printf(",\"titleAudio\":");audio(m->vts_audio_attr,m->nr_of_vts_audio_streams);
            printf(",\"menuSubpictures\":");subp(&m->vtsm_subp_attr,m->nr_of_vtsm_subp_streams);
            printf(",\"titleSubpictures\":");subp(m->vts_subp_attr,m->nr_of_vts_subp_streams);
        }
        putchar('}');
    }
    printf("],\"chapters\":["); int first=1;
    for(unsigned i=1;i<=count;i++) {
        vts_ptt_srpt_t *t=ifo[i]->vts_ptt_srpt;
        for(unsigned j=0;t && j<t->nr_of_srpts;j++) {
            for(unsigned k=0;k<t->title[j].nr_of_ptts;k++) {
                ptt_info_t p=t->title[j].ptt[k];
                printf("%s{\"vts\":%u,\"vtsTitle\":%u,\"chapter\":%u,\"pgc\":%u,\"program\":%u}",first?"":",",i,j+1,k+1,p.pgcn,p.pgn);first=0;
            }
        }
    }
    printf("],\"pgcs\":[");first=1;
    if(ifo[0]->first_play_pgc) { pgc(ifo[0]->first_play_pgc,0,"first-play",0,0,0,ifo[0]->vmgi_mat->vmgm_video_attr);first=0; }
    for(unsigned i=0;i<=count;i++) {
        pgci_ut_t *u=ifo[i]->pgci_ut;
        video_attr_t v=i?ifo[i]->vtsi_mat->vtsm_video_attr:ifo[0]->vmgi_mat->vmgm_video_attr;
        for(unsigned j=0;u && j<u->nr_of_lus;j++) {
            pgcit_t *t=u->lu[j].pgcit;
            for(unsigned k=0;t && k<t->nr_of_pgci_srp;k++) {
                if(!first) putchar(',');
                first=0;
                pgc(t->pgci_srp[k].pgc,(int)i,i?"vts-menu":"vmg-menu",(int)k+1,u->lu[j].lang_code,t->pgci_srp[k].entry_id,v);
            }
        }
        pgcit_t *t=ifo[i]->vts_pgcit;
        for(unsigned k=0;t && k<t->nr_of_pgci_srp;k++) {
            if(!first) putchar(',');
            first=0;
            pgc(t->pgci_srp[k].pgc,(int)i,"title",(int)k+1,0,t->pgci_srp[k].entry_id,ifo[i]->vtsi_mat->vts_video_attr);
        }
    }
    printf("]}\n");
    for(unsigned i=0;i<=count;i++) ifoClose(ifo[i]);
    DVDClose(dvd);return 0;
}
