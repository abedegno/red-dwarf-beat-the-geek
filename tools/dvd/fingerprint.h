/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef DVD_TOOL_FINGERPRINT_H
#define DVD_TOOL_FINGERPRINT_H
#include <stdio.h>
#include <string.h>
#ifdef __APPLE__
#include <CommonCrypto/CommonDigest.h>
#define HASH_CTX CC_SHA256_CTX
#define HASH_INIT CC_SHA256_Init
#define HASH_UPDATE CC_SHA256_Update
#define HASH_FINAL CC_SHA256_Final
#else
#include <openssl/evp.h>
#define HASH_CTX EVP_MD_CTX *
static int hash_init(EVP_MD_CTX **ctx) {
    *ctx = EVP_MD_CTX_new();
    return *ctx && EVP_DigestInit_ex(*ctx, EVP_sha256(), NULL);
}
static int hash_update(EVP_MD_CTX **ctx, const void *data, size_t size) {
    return *ctx && EVP_DigestUpdate(*ctx, data, size);
}
static int hash_final(unsigned char *bytes, EVP_MD_CTX **ctx) {
    int ok = *ctx && EVP_DigestFinal_ex(*ctx, bytes, NULL);
    EVP_MD_CTX_free(*ctx); *ctx = NULL;
    return ok;
}
#define HASH_INIT hash_init
#define HASH_UPDATE hash_update
#define HASH_FINAL hash_final
#endif

static void hex_digest(const unsigned char bytes[32], char hex[65]) {
    for(int i=0;i<32;i++) snprintf(hex+2*i,3,"%02x",bytes[i]);
}
static int fingerprint(const char *dir, unsigned count, char hex[65]) {
    HASH_CTX all; HASH_INIT(&all);
    for(unsigned i=0;i<=count;i++) {
        char name[32],path[4096],line[160],digest_hex[65];
        if(i) snprintf(name,sizeof(name),"VTS_%02u_0.IFO",i);
        else snprintf(name,sizeof(name),"VIDEO_TS.IFO");
        if(snprintf(path,sizeof(path),"%s/%s",dir,name)>=(int)sizeof(path)) return 0;
        FILE *f=fopen(path,"rb");if(!f) return 0;
        HASH_CTX one; HASH_INIT(&one); unsigned char buffer[8192],bytes[32];size_t n;
        while((n=fread(buffer,1,sizeof(buffer),f))) HASH_UPDATE(&one,buffer,(unsigned)n);
        int failed=ferror(f);fclose(f);if(failed) return 0;
        HASH_FINAL(bytes,&one);hex_digest(bytes,digest_hex);
        snprintf(line,sizeof(line),"%sVIDEO_TS/%s:%s",i?"\n":"",name,digest_hex);
        HASH_UPDATE(&all,line,(unsigned)strlen(line));
    }
    unsigned char bytes[32];HASH_FINAL(bytes,&all);hex_digest(bytes,hex);return 1;
}
#endif
