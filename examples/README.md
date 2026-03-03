# Example Files

This directory contains example configurations organized into subfolders by scenario:

- **[vat-exempt/](vat-exempt/)** — Invoice without VAT (Kleinunternehmer §19 UStG)
- **[vat/](vat/)** — Invoice with VAT (7% and 19% rates)
- **[letter/](letter/)** — Letter template

Each subfolder is self-contained with its own `config.example.yml`, data files, and
generated output (PDF, XML, preview PNG).

## Getting started

The first configuration file contains your personal information and settings for the
template (see [vat-exempt/config.example.yml](vat-exempt/config.example.yml) for an
example). Please create a copy named `config.yml` in the project root[^1].

The second file contains information about your customers (see
[vat-exempt/customer.example.csv](vat-exempt/customer.example.csv)). Please create a
copy named `customer.csv`[^2].

Lastly, create a file containing the invoices you want to generate (see
[vat-exempt/invoices.example.yml](vat-exempt/invoices.example.yml) or
[vat/invoices.example.yml](vat/invoices.example.yml)). Please create a copy named
`invoice.yml`[^2].

[^1]: I suggest to place the file in the root directory of the repository.

[^2]: Because this file contains sensitive information, I suggest to place it outside of
    the repository. You can specify the location of the file using the `INVOICE_PATH`
    environment variable. Alternatively, it will default to the `data` directory.
