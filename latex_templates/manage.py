from fire import Fire

from latex_templates import create_cv, create_invoices

if __name__ == "__main__":
    Fire({"invoice": create_invoices, "cv": create_cv})
