#include <iostream>
#include <gpiod.h>
#include <unistd.h>
#include <bitset>
#include <vector>
#include <numeric>
#include <fstream>
#include <ctime>
#include <crow.h>

// Définition des broches
#define DOUT_PIN 5     // GPIO pour DOUT
#define PD_SCK_PIN 6   // GPIO pour PD_SCK

// Fichier CSV pour stocker l'historique des poids
#define HISTORIQUE_POIDS_FILE "historique_poids.csv"

// Fonction pour lire un bit depuis le DOUT
int read_next_bit(struct gpiod_line *dout_line, struct gpiod_line *pd_sck_line) {
    gpiod_line_set_value(pd_sck_line, 1);   // PD_SCK à 1
    usleep(1);  // Attendre pour la stabilité du signal
    gpiod_line_set_value(pd_sck_line, 0);   // PD_SCK à 0

    return gpiod_line_get_value(dout_line);
}

// Fonction pour lire un octet
unsigned char read_next_byte(struct gpiod_line *dout_line, struct gpiod_line *pd_sck_line) {
    unsigned char byte_value = 0;
    for (int i = 0; i < 8; ++i) {
        byte_value <<= 1;
        byte_value |= read_next_bit(dout_line, pd_sck_line);
    }
    return byte_value;
}

// Fonction pour lire les 3 octets de données du HX711
void read_raw_data(struct gpiod_line *dout_line, struct gpiod_line *pd_sck_line, unsigned char &byte1, unsigned char &byte2, unsigned char &byte3) {
    byte1 = read_next_byte(dout_line, pd_sck_line);
    byte2 = read_next_byte(dout_line, pd_sck_line);
    byte3 = read_next_byte(dout_line, pd_sck_line);
}

// Fonction pour convertir la valeur 24 bits en complément à 2
int32_t convert_from_twos_complement(const unsigned char byte1, const unsigned char byte2, const unsigned char byte3) {
    int32_t raw_value = (byte1 << 16) | (byte2 << 8) | byte3;
    if (raw_value & 0x800000) {
        raw_value |= 0xFF000000;
    }
    return raw_value;
}

// Fonction pour effectuer la tare (calibrer l'offset)
int32_t tare(struct gpiod_line *dout_line, struct gpiod_line *pd_sck_line, int num_samples) {
    std::vector<int32_t> readings;
    for (int i = 0; i < num_samples; ++i) {
        unsigned char byte1, byte2, byte3;
        read_raw_data(dout_line, pd_sck_line, byte1, byte2, byte3);
        int32_t value = convert_from_twos_complement(byte1, byte2, byte3);
        readings.push_back(value);
    }
    int32_t sum = std::accumulate(readings.begin(), readings.end(), 0);
    return sum / readings.size();
}

// Fonction pour enregistrer le poids dans un fichier CSV
void save_weight_to_history(float weight) {
    std::ofstream file(HISTORIQUE_POIDS_FILE, std::ios_base::app);
    if (file.is_open()) {
        // Obtenir l'heure actuelle
        std::time_t now = std::time(nullptr);
        std::tm *local_time = std::localtime(&now);
        char timestamp[100];
        std::strftime(timestamp, sizeof(timestamp), "%Y-%m-%d %H:%M:%S", local_time);

        // Enregistrer le poids et l'heure dans le fichier CSV
        file << timestamp << "," << weight << std::endl;
        file.close();
    } else {
        std::cerr << "Erreur lors de l'ouverture du fichier historique." << std::endl;
    }
}

// Fonction pour récupérer l'historique des poids sur une période
std::vector<std::string> get_weight_history() {
    std::vector<std::string> history;
    std::ifstream file(HISTORIQUE_POIDS_FILE);
    std::string line;
    if (file.is_open()) {
        while (std::getline(file, line)) {
            history.push_back(line);
        }
        file.close();
    } else {
        std::cerr << "Erreur lors de la lecture du fichier historique." << std::endl;
    }
    return history;
}

// Fonction principale qui démarre le microservice
int main() {
    struct gpiod_chip *chip = gpiod_chip_open_by_name("gpiochip0");
    if (!chip) {
        std::cerr << "Échec de l'ouverture du GPIO chip!" << std::endl;
        return 1;
    }

    struct gpiod_line *dout_line = gpiod_chip_get_line(chip, DOUT_PIN);
    struct gpiod_line *pd_sck_line = gpiod_chip_get_line(chip, PD_SCK_PIN);
    if (!dout_line || !pd_sck_line) {
        std::cerr << "Erreur lors de l'obtention des lignes GPIO!" << std::endl;
        gpiod_chip_close(chip);
        return 1;
    }

    gpiod_line_request_output(pd_sck_line, "HX711", 0);
    gpiod_line_request_input(dout_line, "HX711");

    // Démarrer le serveur Crow
    crow::SimpleApp app;

    // Route pour lire la valeur brute
    CROW_ROUTE(app, "/read_raw")
    ([]() {
        unsigned char byte1, byte2, byte3;
        read_raw_data(dout_line, pd_sck_line, byte1, byte2, byte3);
        int32_t raw_value = convert_from_twos_complement(byte1, byte2, byte3);
        return crow::json::wvalue{{"raw_value", raw_value}};
    });

    // Route pour effectuer la tare
    CROW_ROUTE(app, "/tare/<int>")
    ([](int num_samples) {
        int32_t tare_value = tare(dout_line, pd_sck_line, num_samples);
        return crow::json::wvalue{{"tare_value", tare_value}};
    });

    // Route pour enregistrer un poids dans l'historique
    CROW_ROUTE(app, "/save_weight/<float>")
    ([](float weight) {
        save_weight_to_history(weight);
        return crow::json::wvalue{{"message", "Poids enregistré avec succès"}};
    });

    // Route pour obtenir l'historique des poids
    CROW_ROUTE(app, "/get_history")
    ([]() {
        std::vector<std::string> history = get_weight_history();
        crow::json::wvalue response;
        for (size_t i = 0; i < history.size(); ++i) {
            response["history"][i] = history[i];
        }
        return response;
    });

    // Lancer le serveur sur le port 8080
    app.port(8080).multithreaded().run();

    // Fermer le chip GPIO
    gpiod_chip_close(chip);
    return 0;
}
