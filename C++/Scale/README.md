Installer Boost (si ce n'est pas déjà fait) :

```bash
sudo apt-get install libboost-all-dev
```
Installer Crow : Clonez le dépôt Crow depuis GitHub :

```bash
git clone https://github.com/CrowCpp/Crow.git
cd Crow
mkdir build
cd build
cmake ..
make
sudo make install
```

Assurez-vous que vous avez les dépendances nécessaires : Vous aurez besoin de CMake et de Boost. Installez-les si nécessaire :

```bash
sudo apt-get install cmake
sudo apt-get install libboost-all-dev
```

curl http://localhost:8080/read_raw
curl http://localhost:8080/tare/10
curl http://localhost:8080/save_weight/72.5
curl http://localhost:8080/get_history