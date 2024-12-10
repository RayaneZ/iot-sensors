#include <iostream>

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
