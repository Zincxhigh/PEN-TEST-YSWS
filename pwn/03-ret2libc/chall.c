#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

int main() {
    setvbuf(stdout, NULL, _IONBF, 0);
    setvbuf(stdin, NULL, _IONBF, 0);
    char buf[128];

    puts("Welcome to ret2libc.");
    puts("Leak something:");
    ssize_t n = read(STDIN_FILENO, buf, 120);
    if (n <= 0) exit(1);
    buf[n] = '\0';
    if (buf[n - 1] == '\n') buf[n - 1] = '\0';
    printf(buf);  
    printf("puts = %p\n", (void*)puts);

    puts("Say something big:");
    read(STDIN_FILENO, buf, 256);  
    return 0;
}
