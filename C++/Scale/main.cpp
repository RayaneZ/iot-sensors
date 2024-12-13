#include <gpiod.h>
#include <chrono>
#include <thread>
#include <cstdint>
#include <iostream>

class HX711 {
public:
    HX711(const char* chipname, int dout, int pd_sck, uint8_t gain = 128);
    ~HX711();
    void begin();
    bool is_ready();
    void set_gain(uint8_t gain);
    long read();
    void wait_ready(unsigned long delay_ms = 0.001);
    void power_down();
    void power_up();

private:
    const char* chipname;
    int dout_pin;
    int pd_sck_pin;
    uint8_t GAIN;
    struct gpiod_chip* chip;
    struct gpiod_line* dout_line;
    struct gpiod_line* pd_sck_line;

    void pulse_sck();
    uint8_t shift_in();
};

HX711::HX711(const char* chipname, int dout, int pd_sck, uint8_t gain)
    : chipname(chipname), dout_pin(dout), pd_sck_pin(pd_sck), GAIN(1) {
    set_gain(gain);
}

HX711::~HX711() {
    gpiod_line_release(dout_line);
    gpiod_line_release(pd_sck_line);
    gpiod_chip_close(chip);
}

void HX711::begin() {
    chip = gpiod_chip_open_by_name(chipname);
    if (!chip) {
        throw std::runtime_error("Failed to open GPIO chip");
    }

    dout_line = gpiod_chip_get_line(chip, dout_pin);
    pd_sck_line = gpiod_chip_get_line(chip, pd_sck_pin);

    if (!dout_line || !pd_sck_line) {
        throw std::runtime_error("Failed to get GPIO lines");
    }

    gpiod_line_request_input(dout_line, "hx711_dout");
    gpiod_line_request_output(pd_sck_line, "hx711_pd_sck", 0);
}

bool HX711::is_ready() {
    return gpiod_line_get_value(dout_line) == 0;
}

void HX711::set_gain(uint8_t gain) {
    switch (gain) {
        case 128: GAIN = 1; break;
        case 64:  GAIN = 3; break;
        case 32:  GAIN = 2; break;
        default: throw std::invalid_argument("Invalid gain");
    }
}

void HX711::pulse_sck() {
    gpiod_line_set_value(pd_sck_line, 1);
    std::this_thread::sleep_for(std::chrono::microseconds(1));
    gpiod_line_set_value(pd_sck_line, 0);
    std::this_thread::sleep_for(std::chrono::microseconds(1));
}

uint8_t HX711::shift_in() {
    uint8_t value = 0;
    for (int i = 0; i < 8; ++i) {
        pulse_sck();
        value |= (gpiod_line_get_value(dout_line) << (7 - i));
    }
    return value;
}

long HX711::read() {
    wait_ready();
    uint8_t data[3] = {0};

    for (int i = 2; i >= 0; --i) {
        data[i] = shift_in();
    }

    for (int i = 0; i < GAIN; ++i) {
        pulse_sck();
    }

    // Combine bytes into signed 32-bit value
    long value = ((data[2] & 0x80) ? 0xFF000000 : 0x00) |
                 (data[2] << 16) |
                 (data[1] << 8) |
                 data[0];

    return value;
}

void HX711::wait_ready(unsigned long delay_ms) {
    while (!is_ready()) {
        std::this_thread::sleep_for(std::chrono::milliseconds(delay_ms));
    }
}

void HX711::power_down() {
    gpiod_line_set_value(pd_sck_line, 0);
    gpiod_line_set_value(pd_sck_line, 1);
    std::this_thread::sleep_for(std::chrono::microseconds(70));
}

void HX711::power_up() {
    gpiod_line_set_value(pd_sck_line, 0);
}


int main() {
    try {
        HX711 scale("gpiochip0", 149, 200, 128); // Example GPIO pins
        scale.begin();

        while (true) {
            if (scale.is_ready()) {
                long reading = scale.read();
                std::cout << "Reading: " << reading << std::endl;
            } else {
                std::cout << "Waiting for HX711..." << std::endl;
            }
            std::this_thread::sleep_for(std::chrono::milliseconds(500));
        }
    } catch (const std::exception& e) {
        std::cerr << "Error: " << e.what() << std::endl;
    }

    return 0;
}
