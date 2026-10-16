#include "v4_index.hpp"

#include <iostream>
#include <sstream>

static void show(const std::vector<std::string>& groups) {
    if (groups.empty()) { std::cout << "(no groups)\n"; return; }
    for (std::size_t i = 0; i < groups.size(); ++i) {
        if (i) std::cout << ", ";
        std::cout << groups[i];
    }
    std::cout << '\n';
}

int main(int argc, char** argv) {
    if (argc != 2) { std::cerr << "Usage: demo_v4 students.csv\n"; return 2; }
    try {
        V4Index db(read_students(argv[1]));
        std::cout << "Commands: count | move EMAIL GROUP | average | quit\n";
        std::string line;
        while (std::getline(std::cin, line)) {
            std::istringstream input(line);
            std::string command, email, group, extra;
            input >> command;
            if (command == "quit") break;
            if (command == "count") show(db.largest_groups());
            else if (command == "average") show(db.highest_average_groups());
            else if (command == "move" && input >> email >> group && !(input >> extra)) {
                std::cout << (db.change_group(email, group) ? "changed" : "email not found") << '\n';
            } else std::cout << "Commands: count | move EMAIL GROUP | average | quit\n";
        }
        if (!db.validate()) { std::cerr << "Index consistency check failed\n"; return 1; }
    } catch (const std::exception& e) {
        std::cerr << e.what() << '\n';
        return 1;
    }
}
