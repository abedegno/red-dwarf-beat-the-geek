/* SPDX-License-Identifier: GPL-2.0-or-later */
#include <stdio.h>
#include <stdint.h>
#include <string.h>
#include <dvdread/nav_read.h>

static void string(const char *s) {
    putchar('"');
    for(;*s;s++) {
        unsigned char c=(unsigned char)*s;
        if(c=='"' || c=='\\') { putchar('\\');putchar(c); }
        else if(c<32) printf("\\u%04x",c);
        else putchar(c);
    }
    putchar('"');
}
static void emit(pci_t *p, const char *file, unsigned sector, const char *fp) {
    hl_gi_t *h=&p->hli.hl_gi;
    if(!(h->hli_ss & 3)) return;
    unsigned groups=h->btngr_ns;
    if(groups<1 || groups>3 || h->btn_ns>36/groups) {
        fprintf(stderr,"Invalid button group/count at sector %u\n",sector);return;
    }
    unsigned display[3]={h->btngr1_dsp_ty,h->btngr2_dsp_ty,h->btngr3_dsp_ty};
    for(unsigned g=0;g<groups;g++) for(unsigned b=0;b<h->btn_ns;b++) {
        btni_t *t=&p->hli.btnit[g*(36/groups)+b];
        printf("{\"schemaVersion\":1,\"sourceFingerprint\":");if(fp) string(fp);else printf("null");
        printf(",\"vob\":");string(file);
        printf(",\"sector\":%u,\"navSector\":%u,\"vobuStart\":%u,\"vobuEnd\":%u,\"highlightStatus\":%u,\"highlightStart\":%u,\"highlightEnd\":%u,\"selectionEnd\":%u,\"forcedSelect\":%u,\"forcedActivate\":%u,\"group\":%u,\"displayMode\":%u,\"button\":%u,\"buttonOffset\":%u,\"autoAction\":%u,\"rectangle\":[%u,%u,%u,%u],\"neighbours\":{\"up\":%u,\"down\":%u,\"left\":%u,\"right\":%u},\"colourIndex\":%u,\"colourTable\":[",
            sector,p->pci_gi.nv_pck_lbn,p->pci_gi.vobu_s_ptm,p->pci_gi.vobu_e_ptm,h->hli_ss,h->hli_s_ptm,h->hli_e_ptm,h->btn_se_e_ptm,h->fosl_btnn,h->foac_btnn,g+1,display[g],b+1,h->btn_ofn,t->auto_action_mode,t->x_start,t->y_start,t->x_end,t->y_end,t->up,t->down,t->left,t->right,t->btn_coln);
        for(unsigned i=0;i<3;i++) printf("%s[%u,%u]",i?",":"",p->hli.btn_colit.btn_coli[i][0],p->hli.btn_colit.btn_coli[i][1]);
        printf("],\"command\":\"");for(unsigned i=0;i<8;i++) printf("%02x",t->cmd.bytes[i]);
        printf("\"}\n");
    }
}
int main(int argc,char **argv) {
    if(argc<2 || argc>3) { fprintf(stderr,"Usage: inspect_nav VOB [source-fingerprint]\n");return 2; }
    FILE *f=fopen(argv[1],"rb");if(!f) { perror(argv[1]);return 1; }
    unsigned char block[2048];unsigned sector=0,unknown=0;size_t n;
    while((n=fread(block,1,sizeof(block),f))) {
        if(n!=sizeof(block)) { fprintf(stderr,"truncated sector %u\n",sector);fclose(f);return 1; }
        if(memcmp(block,"\0\0\1\xba",4)) { unknown++;sector++;continue; }
        size_t offset=14+(block[13]&7);
        while(offset+6<=sizeof(block) && !memcmp(block+offset,"\0\0\1",3)) {
            unsigned length=((unsigned)block[offset+4]<<8)|block[offset+5];
            if(offset+6+length>sizeof(block)) break;
            if(block[offset+3]==0xbf && length>=PCI_BYTES && block[offset+6]==0) {
                pci_t pci;navRead_PCI(&pci,block+offset+7);emit(&pci,argv[1],sector,argc==3?argv[2]:NULL);
            }
            if(!length) break;
            offset+=6+length;
        }
        sector++;
    }
    int error=ferror(f);fclose(f);
    if(unknown) fprintf(stderr,"Unrecognised pack headers: %u sectors\n",unknown);
    return error || unknown ? 1 : 0;
}
