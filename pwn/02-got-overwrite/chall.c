#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

void win() {
    char flag[128];
    FILE *f = fopen("./flag.txt", "r");
    if (!f) { puts("no flag.txt"); exit(1); }
    if (fgets(flag, sizeof(flag), f))
        printf("FLAG: %s", flag);
    fclose(f);
}

int main() {
    setvbuf(stdout, NULL, _IONBF, 0);
    setvbuf(stdin, NULL, _IONBF, 0);
    char buf[64];

    printf("main = %p\n", (void*)main);

    puts("Say something:");
    ssize_t n = read(STDIN_FILENO, buf, sizeof(buf) - 1);
    if (n <= 0) exit(1);
    buf[n] = '\0';
    if (buf[n - 1] == '\n') buf[n - 1] = '\0';  
    printf(buf);         
    puts("Bye.");
    exit(0);
}
