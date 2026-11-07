/* SPDX-License-Identifier: GPL-2.0-or-later
 * Separate offline extras tracer; the accepted quiz oracle is unchanged.
 */
#define main accepted_round_oracle_main
#include "oracle.c"
#undef main

static void emit_extras(vm_t *vm) {
    dvd_state_t *s=&vm->state;
    printf("{\"vts\":%d,\"domain\":%d,\"pgc\":%d,\"cell\":%d,\"program\":%d,\"audio\":%u,\"selected\":%u,\"subpicture\":%u,\"registers\":[",
        (s->domain==DVD_DOMAIN_VTSMenu || s->domain==DVD_DOMAIN_VTSTitle)?s->vtsN:0,s->domain,s->pgcN,s->cellN,s->pgN,s->registers.SPRM[1],s->registers.SPRM[8]>>10,s->registers.SPRM[2]);
    for(int i=0;i<16;i++)printf("%s%u",i?",":"",s->registers.GPRM[i]);
    printf("],\"stopped\":%s}\n",vm->stopped?"true":"false");fflush(stdout);
}

int main(int argc,char **argv) {
    if(argc!=2)return 2;
    dvdnav_logger_cb log={logger};vm_t *vm=vm_new_vm(NULL,&log),*saved[512]={0};
    if(!vm || !vm_reset(vm,argv[1],NULL,NULL))return 1;
    char line[2048];int result=0;
    while(fgets(line,sizeof(line),stdin)) {
        if(!strncmp(line,"quit",4))break;
        int vts,pgc,seed,button,slot,consumed;
        if(sscanf(line,"start %d %d %d %n",&vts,&pgc,&seed,&consumed)==3) {
            unsigned values[16];char *cursor=line+consumed;
            if(vts<2 || vts>15 || pgc<1){result=2;break;}
            for(int i=0;i<16;i++) {
                int n;if(sscanf(cursor,"%u%n",&values[i],&n)!=1 || values[i]>65535){result=2;break;}
                cursor+=n;
            }
            if(result)break;
            if(!ifoOpenNewVTSI(vm,vm->dvd,vts)){result=1;break;}
            vm->state.domain=DVD_DOMAIN_VTSMenu;vm->stopped=0;
            memset(vm->state.registers.GPRM_mode,0,sizeof(vm->state.registers.GPRM_mode));
            for(int i=0;i<16;i++)vm->state.registers.GPRM[i]=values[i];
            vm->state.registers.SPRM[1]=0;vm->state.registers.SPRM[2]=0;vm->state.registers.SPRM[8]=0;
            srand((unsigned)seed);
            vm_cmd_t cmd={{0x20,4,0,0,0,0,(uint8_t)(pgc>>8),(uint8_t)pgc}};
            if(!vm_exec_cmd(vm,&cmd)){result=1;break;}
        } else if(sscanf(line,"save %d",&slot)==1) {
            if(slot<0 || slot>=512){result=2;break;}
            if(saved[slot])vm_free_copy(saved[slot]);
            saved[slot]=vm_new_copy(vm);if(!saved[slot]){result=1;break;}
        } else if(sscanf(line,"restore %d",&slot)==1) {
            if(slot<0 || slot>=512 || !saved[slot]){result=2;break;}
            vm_t *copy=vm_new_copy(saved[slot]);if(!copy){result=1;break;}
            vm_merge(vm,copy);vm_free_copy(copy);
        } else if(sscanf(line,"seed %d",&seed)==1) {
            srand((unsigned)seed);
        } else if(!strncmp(line,"cell",4)) {
            vm_get_next_cell(vm);
        } else if(sscanf(line,"select %d",&button)==1) {
            if(button<1 || button>36){result=2;break;}set_HL_BTN(vm,button);
        } else if(!strncmp(line,"answer ",7) && strlen(line)>=23) {
            vm_cmd_t cmd;
            for(int i=0;i<8;i++){unsigned byte;if(sscanf(line+7+i*2,"%2x",&byte)!=1){result=2;break;}cmd.bytes[i]=(uint8_t)byte;}
            if(result)break;vm_exec_cmd(vm,&cmd);
        } else if(strncmp(line,"peek",4)) {result=2;break;}
        emit_extras(vm);
    }
    for(int i=0;i<512;i++)if(saved[i])vm_free_copy(saved[i]);
    vm_free_vm(vm);return result;
}
