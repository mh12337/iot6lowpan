#include <iostream>
#include <cstring>
#include <unistd.h>
#include <sys/socket.h>
#include <linux/if_ieee802154.h>

int main() {
    int sock = socket(AF_IEEE802154, SOCK_DGRAM, 0);
    if (sock < 0) {
        perror("socket");
        return 1;
    }

    sockaddr_ieee802154 addr{};
    addr.family = AF_IEEE802154;
    addr.addr.addr_type = IEEE802154_ADDR_SHORT;
    addr.addr.short_addr = 0x0001;   // receiver address
    addr.addr.pan_id = 0x1234;

    if (bind(sock, (struct sockaddr*)&addr, sizeof(addr)) < 0) {
        perror("bind");
        return 1;
    }

    std::cout << "Receiver ready...\n";

    char buffer[128];

    while (true) {
        ssize_t len = recv(sock, buffer, sizeof(buffer), 0);
        if (len < 0) {
            perror("recv");
            break;
        }

        std::cout << "Received (" << len << " bytes): ";
        std::cout.write(buffer, len);
        std::cout << std::endl;
    }

    close(sock);
    return 0;
}