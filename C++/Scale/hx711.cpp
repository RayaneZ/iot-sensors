#include <iostream>
#include <gpiod.h>
#include <unistd.h>
#include <bitset>
#include <vector>
#include <numeric>
#include <fstream>
#include <ctime>
#include <string>
#include <sstream>
#include <netinet/in.h>

// Define GPIO pins
#define DOUT_PIN 149 
#define PD_SCK_PIN 200 

// File for storing weight history
#define HISTORIQUE_POIDS_FILE "historique_poids.csv"

// Function to read a bit from DOUT
int read_next_bit(struct gpiod_line *dout_line, struct gpiod_line *pd_sck_line) {
    gpiod_line_set_value(pd_sck_line, 1);
    usleep(1); // Small delay to ensure timing
    gpiod_line_set_value(pd_sck_line, 0);
    return gpiod_line_get_value(dout_line);
}

// Function to read a byte
unsigned char read_next_byte(struct gpiod_line *dout_line, struct gpiod_line *pd_sck_line) {
    unsigned char byte_value = 0;
    for (int i = 0; i < 8; ++i) {
        byte_value <<= 1;
        byte_value |= read_next_bit(dout_line, pd_sck_line);
    }
    return byte_value;
}

// Function to read 3 bytes of data from HX711
void read_raw_data(struct gpiod_line *dout_line, struct gpiod_line *pd_sck_line, unsigned char &byte1, unsigned char &byte2, unsigned char &byte3) {
    byte1 = read_next_byte(dout_line, pd_sck_line);
    byte2 = read_next_byte(dout_line, pd_sck_line);
    byte3 = read_next_byte(dout_line, pd_sck_line);

    // Debugging raw bytes
    std::cout << "Byte 1: " << (int)byte1 << " Byte 2: " << (int)byte2 << " Byte 3: " << (int)byte3 << std::endl;
}

// Function to convert 24-bit value from two's complement
int32_t convert_from_twos_complement(const unsigned char byte1, const unsigned char byte2, const unsigned char byte3) {
    int32_t raw_value = (byte1 << 16) | (byte2 << 8) | byte3;
    if (raw_value & 0x800000) {
        raw_value |= 0xFF000000;  // Extend sign for two's complement
    }
    return raw_value;
}

// Function to tare (calibrate offset)
int32_t tare(struct gpiod_line *dout_line, struct gpiod_line *pd_sck_line, int num_samples) {
    std::vector<int32_t> readings;
    for (int i = 0; i < num_samples; ++i) {
        unsigned char byte1, byte2, byte3;
        read_raw_data(dout_line, pd_sck_line, byte1, byte2, byte3);
        int32_t raw_value = convert_from_twos_complement(byte1, byte2, byte3);
        readings.push_back(raw_value);
    }
    int32_t sum = std::accumulate(readings.begin(), readings.end(), 0);
    return sum / readings.size();
}

// Function to calculate weight from raw value
float calculate_weight(int32_t raw_value, float scale) {
    return raw_value / scale;
}

// Function to save weight to CSV
void save_weight_to_history(float weight) {
    std::ofstream file(HISTORIQUE_POIDS_FILE, std::ios_base::app);
    if (file.is_open()) {
        std::time_t now = std::time(nullptr);
        char timestamp[100];
        std::strftime(timestamp, sizeof(timestamp), "%Y-%m-%d %H:%M:%S", std::localtime(&now));
        file << timestamp << "," << weight << "\n";
        file.close();
    }
}

// Function to retrieve weight history
std::string get_weight_history() {
    std::ifstream file(HISTORIQUE_POIDS_FILE);
    std::stringstream history;
    std::string line;
    if (file.is_open()) {
        while (std::getline(file, line)) {
            history << line << "\n";
        }
        file.close();
    }
    return history.str();
}

// HTTP response helper
std::string build_response(const std::string &body, const std::string &content_type = "text/plain") {
    std::ostringstream response;
    response << "HTTP/1.1 200 OK\r\n";
    response << "Content-Type: " << content_type << "\r\n";
    response << "Content-Length: " << body.size() << "\r\n";
    response << "\r\n";
    response << body;
    return response.str();
}

int main() {
    // GPIO setup
    struct gpiod_chip *chip = gpiod_chip_open_by_name("gpiochip0");
    if (!chip) {
        std::cerr << "Failed to open GPIO chip!\n";
        return 1;
    }

    struct gpiod_line *dout_line = gpiod_chip_get_line(chip, DOUT_PIN);
    struct gpiod_line *pd_sck_line = gpiod_chip_get_line(chip, PD_SCK_PIN);
    if (!dout_line || !pd_sck_line) {
        std::cerr << "Failed to get GPIO lines!\n";
        gpiod_chip_close(chip);
        return 1;
    }

    gpiod_line_request_output(pd_sck_line, "HX711", 0);
    gpiod_line_request_input(dout_line, "HX711");

    // Set up a simple HTTP server
    int server_fd = socket(AF_INET, SOCK_STREAM, 0);
    if (server_fd == -1) {
        perror("Socket creation failed");
        return 1;
    }

    sockaddr_in server_addr{};
    server_addr.sin_family = AF_INET;
    server_addr.sin_addr.s_addr = INADDR_ANY;
    server_addr.sin_port = htons(8080);

    if (bind(server_fd, (sockaddr *)&server_addr, sizeof(server_addr)) == -1) {
        perror("Bind failed");
        close(server_fd);
        return 1;
    }

    if (listen(server_fd, 5) == -1) {
        perror("Listen failed");
        close(server_fd);
        return 1;
    }

    std::cout << "Server is running on port 8080...\n";

    while (true) {
        int client_fd = accept(server_fd, nullptr, nullptr);
        if (client_fd == -1) {
            perror("Accept failed");
            continue;
        }

        char buffer[4096];
        ssize_t bytes_read = read(client_fd, buffer, sizeof(buffer) - 1);
        if (bytes_read > 0) {
            buffer[bytes_read] = '\0';
            std::string request(buffer);

            // Handle specific routes
            std::string response;
            if (request.find("GET /read_raw") == 0) {
                unsigned char byte1, byte2, byte3;
                read_raw_data(dout_line, pd_sck_line, byte1, byte2, byte3);
                int32_t raw_value = convert_from_twos_complement(byte1, byte2, byte3);
                std::cout << "Raw Value: " << raw_value << std::endl;  // Debugging the raw value
                float weight = calculate_weight(raw_value, 1000);  // Example scale value
                std::cout << "Weight: " << weight << std::endl;  // Debugging weight calculation
                response = build_response("Raw Value: " + std::to_string(raw_value) + "\nWeight: " + std::to_string(weight));
            } else if (request.find("GET /get_history") == 0) {
                response = build_response(get_weight_history());
            } else {
                response = build_response("Unknown route", "text/plain");
            }

            write(client_fd, response.c_str(), response.size());
        }
        close(client_fd);
    }

    gpiod_chip_close(chip);
    return 0;
}
