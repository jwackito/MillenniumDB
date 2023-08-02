#pragma once

#include <memory>

#include "graph_models/object_id.h"
#include "graph_models/rdf_model/conversions.h"
#include "query/executor/binding_iter/binding_expr/binding_expr.h"
#include "third_party/hashes/sha512.h"

namespace SPARQL {
class BindingExprSHA512 : public BindingExpr {
public:
    std::unique_ptr<BindingExpr> expr;

    BindingExprSHA512(std::unique_ptr<BindingExpr> expr) :
        expr (std::move(expr)) { }

    ObjectId eval(const Binding& binding) override {
        auto expr_oid = expr->eval(binding);

        if (expr_oid.get_sub_type() == ObjectId::MASK_STRING_SIMPLE) {
            SHA512      sha512;
            std::string str  = Conversions::unpack_string_simple(expr_oid);
            std::string hash = sha512.hash(str);
            return Conversions::pack_string_simple(hash);
        } else {
            return ObjectId::get_null();
        }
    }

    std::ostream& print_to_ostream(std::ostream& os) const override {
        os << "SHA512(" << *expr << ")";
        return os;
    }
};
} // namespace SPARQL
