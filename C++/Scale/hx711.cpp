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
#include <chrono>  // For time measurement

// Define GPIO pins
#define DOUT_PIN 149 
#define PD_SCK_PIN 200 

// File for storing weight history
#define HISTORIQUE_POIDS_FILE "historique_poids.csv"

// Function to read a bit from DOUT
int read_next_bit(struct gpiod_line *dout_line, struct gpiod_line *pd_sck_line) {
    gpiod_line_set_value(pd_sck_line, 1);
    usleep(1);  // Adjust the timing here as needed
    gpiod_line_set_value(pd_sck_line, 0);
    usleep(1);  // Adjust the timing here as needed
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
    usleep(1);  // Add delay between reads if necessary
    byte2 = read_next_byte(dout_line, pd_sck_line);
    usleep(1);  // Add delay between reads if necessary
    byte3 = read_next_byte(dout_line, pd_sck_line);
}

// Function to convert 24-bit value from two's complement
int32_t convert_from_twos_complement(const unsigned char byte1, const unsigned char byte2, const unsigned char byte3) {
    int32_t raw_value = (byte1 << 16) | (byte2 << 8) | byte3;
    if (raw_value & 0x800000) {
        raw_value |= 0xFF000000;
    }
    return raw_value;
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

    // Time measurement variables
    auto last_read_time = std::chrono::steady_clock::now();

    while (true) {
        unsigned char byte1, byte2, byte3;
        read_raw_data(dout_line, pd_sck_line, byte1, byte2, byte3);
        int32_t raw_value = convert_from_twos_complement(byte1, byte2, byte3);

        // Get the current time
        auto current_time = std::chrono::steady_clock::now();
        std::chrono::duration<double> time_diff = current_time - last_read_time;
        last_read_time = current_time;

        // Print the time between readings and the raw value
        std::cout << "Time since last reading: " << time_diff.count() << " seconds\n";
        std::cout << "Raw Value: " << raw_value << std::endl;
    }

    gpiod_chip_close(chip);
    return 0;
}
