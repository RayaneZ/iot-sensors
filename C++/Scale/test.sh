#!/bin/bash

# Boucle pour tester chaque GPIO de 0 à 27 (ajustez la plage si nécessaire)
for gpio in {0..27}
do
    echo "Test du GPIO $gpio"

    # Vérifie la valeur initiale du GPIO (devrait être 0 si non configuré autrement)
    initial_value=$(gpioget gpiochip0 $gpio)
    echo "Valeur initiale de GPIO$gpio : $initial_value"

    # Configurer le GPIO en sortie et le mettre à 1 (haut)
    gpioset gpiochip0 $gpio=1
    # Attendre 5 secondes
    sleep 5

    # Vérifie la valeur après avoir mis à 1
    value_after_set=$(gpioget gpiochip0 $gpio)
    echo "Valeur après mise à 1 de GPIO$gpio : $value_after_set"

    # Mettre le GPIO à 0 (bas)
    gpioset gpiochip0 $gpio=0

    # Vérifie la valeur après avoir mis à 0
    value_after_reset=$(gpioget gpiochip0 $gpio)
    echo "Valeur après remise à 0 de GPIO$gpio : $value_after_reset"

    # Ajouter une ligne vide pour mieux séparer les tests
    echo
done

echo "Test terminé."
