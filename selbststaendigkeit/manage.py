from fire import Fire

from selbststaendigkeit.templates.invoice import create_invoice

if __name__ == "__main__":
    Fire({"invoice": create_invoice})
