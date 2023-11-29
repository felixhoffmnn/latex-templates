from fire import Fire

from latex_templates.invoice.template import create_invoice

if __name__ == "__main__":
    Fire({"invoice": create_invoice})
