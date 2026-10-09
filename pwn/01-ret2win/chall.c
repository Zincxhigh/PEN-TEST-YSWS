#include <stdio.h>
#include <stdlib.h>

void win() {
    char flag[128];
    FILE *f = fopen("./flag.txt", "r");
    if (!f) { puts("no flag.txt"); exit(1); }
    if (fgets(flag, sizeof(flag), f))
        printf("FLAG: %s", flag);
    fclose(f);
}

void vuln() {
    char buf[64];
    puts("Say something:");
    gets(buf); 
    printf("You said: %s\n", buf);
}

int main() {
    setvbuf(stdout, NULL, _IONBF, 0);
    setvbuf(stdin, NULL, _IONBF, 0);
    vuln();
    return 0;
}
