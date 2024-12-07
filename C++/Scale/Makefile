CXX = g++
CXXFLAGS = -std=c++11 -Wall -O2
LIBS = -lgpiod -lcrow

TARGET = hx711

SRCS = hx711.cpp

OBJDIR = obj

$(OBJDIR):
	mkdir -p $(OBJDIR)

all: $(TARGET)

$(OBJDIR)/%.o: %.cpp | $(OBJDIR)
	$(CXX) $(CXXFLAGS) -c $< -o $@

$(TARGET): $(OBJDIR)/hx711.o
	$(CXX) $(CXXFLAGS) $^ -o $@ $(LIBS)

clean:
	rm -rf $(OBJDIR) $(TARGET)

run: $(TARGET)
	sudo ./$(TARGET)
