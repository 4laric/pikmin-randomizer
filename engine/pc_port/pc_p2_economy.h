#pragma once
#include <map>
#include <string>

// A receipt ledger only; cave/squad checkpoints are a separate lifecycle layer.
class P2Economy {
    std::map<std::string,int> receipts;
    std::string path;
public:
    void load(const std::string& file);
    bool credit(const std::string& id,int value);
    int total() const;
    size_t count() const { return receipts.size(); }
};
