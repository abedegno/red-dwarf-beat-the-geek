/* SPDX-License-Identifier: GPL-2.0-or-later
 * Offline source normalization only. Never linked into the browser application.
 */
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <stdarg.h>
#include <sys/time.h>
#include <dvdnav/dvdnav.h>
#include "vm/decoder.h"
#include "vm/vm.h"
#include "vm/getset.h"
#include "dvdnav_internal.h"

static void logger(void *p,dvdnav_logger_level_t l,const char *fmt,va_list args) {
    (void)p;if(l==DVDNAV_LOGGER_LEVEL_ERROR) {vfprintf(stderr,fmt,args);fputc('\n',stderr);}
}
static void emit(vm_t *vm) {
    dvd_state_t *s=&vm->state;
    printf("{\"vts\":%d,\"domain\":%d,\"pgc\":%d,\"cell\":%d,\"program\":%d,\"score\":%u,\"remaining\":%u,\"variant\":%u,\"candidate\":%u,\"audio\":%u,\"registers\":[",
        s->vtsN,s->domain,s->pgcN,s->cellN,s->pgN,s->registers.GPRM[1]%100,s->registers.GPRM[13],
        s->registers.GPRM[12],s->registers.GPRM[10],s->registers.SPRM[1]);
    for(int i=0;i<16;i++)printf("%s%u",i?",":"",s->registers.GPRM[i]);
    printf("]}\n");fflush(stdout);
}
int main(int argc,char **argv) {
    if(argc!=2)return 2;
    dvdnav_logger_cb log={logger};vm_t *vm=vm_new_vm(NULL,&log);
    if(!vm || !vm_reset(vm,argv[1],NULL,NULL))return 1;
    char line[256];
    while(fgets(line,sizeof(line),stdin)) {
        if(!strncmp(line,"quit",4))break;
        int vts,pgc,mask,variant,score,remaining,seed,total,mode,p1,p2,t1,t2;
        if(sscanf(line,"two %d %d %d %d %d %d %d %d %d %d %d",&vts,&pgc,&mode,&mask,&variant,&p1,&p2,&t1,&t2,&remaining,&seed)==11) {
            int a=(mode%1000)/100,b=(mode%10000)/1000;
            if(mode!=10000+b*1000+a*100+21 || a<1 || a>3 || b<1 || b>3)return 2;
            if(vts<2 || vts>10 || pgc<1 || p1<0 || p1>6 || p2<0 || p2>6 || t1<p1 || t1>48 || t2<p2 || t2>48 || remaining<0 || remaining>13)return 2;
            if(mask<0 || mask>32768 || variant<1 || variant>4)return 2;
            if(!ifoOpenNewVTSI(vm,vm->dvd,vts))return 1;
            vm->state.domain=DVD_DOMAIN_VTSMenu;vm->stopped=0;
            memset(vm->state.registers.GPRM,0,sizeof(vm->state.registers.GPRM));
            memset(vm->state.registers.GPRM_mode,0,sizeof(vm->state.registers.GPRM_mode));
            vm->state.registers.GPRM[0]=mode;
            vm->state.registers.GPRM[1]=10000+t1+100*t2;
            vm->state.registers.GPRM[3]=p1+10*p2;
            vm->state.registers.GPRM[10]=mask;vm->state.registers.GPRM[11]=mask;
            vm->state.registers.GPRM[12]=variant;vm->state.registers.GPRM[13]=remaining;
            vm->state.registers.SPRM[1]=0;vm->state.registers.SPRM[8]=0;
            srand((unsigned)seed);
            vm_cmd_t cmd={{0x20,4,0,0,0,0,(uint8_t)(pgc>>8),(uint8_t)pgc}};
            if(!vm_exec_cmd(vm,&cmd))return 1;
            emit(vm);continue;
        }
        int fields=sscanf(line,"start %d %d %d %d %d %d %d %d %d",&vts,&pgc,&mask,&variant,&score,&remaining,&seed,&total,&mode);
        if(fields>=7) {
            if(fields==7)total=score;
            if(fields<9)mode=10101;
            if(mode!=10101 && mode!=10201 && mode!=10301 && mode!=10102 && mode!=10202 && mode!=10302)return 2;
            if(vts<1 || vts>15 || pgc<1 || score<0 || score>6 || remaining<0 || remaining>7)return 2;
            if(total<score || total>48)return 2;
            if(!ifoOpenNewVTSI(vm,vm->dvd,vts))return 1;
            vm->state.domain=DVD_DOMAIN_VTSMenu;vm->stopped=0;
            memset(vm->state.registers.GPRM,0,sizeof(vm->state.registers.GPRM));
            memset(vm->state.registers.GPRM_mode,0,sizeof(vm->state.registers.GPRM_mode));
            vm->state.registers.GPRM[0]=mode;
            vm->state.registers.GPRM[1]=10000+total;
            vm->state.registers.GPRM[3]=score;
            vm->state.registers.GPRM[(mode%1000)/100+3]=mask;
            vm->state.registers.GPRM[10]=mask;
            vm->state.registers.GPRM[11]=mask;
            vm->state.registers.GPRM[12]=variant;
            vm->state.registers.GPRM[13]=remaining;
            vm->state.registers.SPRM[1]=0;
            srand((unsigned)seed);
            vm_cmd_t cmd={{0x20,4,0,0,0,0,(uint8_t)(pgc>>8),(uint8_t)pgc}};
            if(!vm_exec_cmd(vm,&cmd))return 1;
        } else if(!strncmp(line,"cell",4)) {
            vm_get_next_cell(vm);
        } else if(sscanf(line,"select %d",&mask)==1) {
            if(mask<1 || mask>36)return 2;
            set_HL_BTN(vm,mask);
        } else if(!strncmp(line,"answer ",7)) {
            vm_cmd_t cmd;
            for(int i=0;i<8;i++){unsigned b;if(sscanf(line+7+2*i,"%2x",&b)!=1)return 2;cmd.bytes[i]=(uint8_t)b;}
            vm_exec_cmd(vm,&cmd);
        } else return 2;
        emit(vm);
    }
    vm_free_vm(vm);return 0;
}
