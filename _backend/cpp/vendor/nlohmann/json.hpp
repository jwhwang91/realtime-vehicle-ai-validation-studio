#pragma once
// Minimal placeholder so the mock source tree mirrors a production-style vendor layout.
// For real JSON parsing, replace this with the official nlohmann/json single header.
#include <map>
#include <string>
namespace nlohmann {
class json : public std::map<std::string, std::string> {
public:
    static json parse(const std::string&) { return {}; }
    std::string dump() const { return "{}"; }
};
}
