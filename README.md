# Latex Templates

> :warning: This project only supports **German** currently

This project is intended to be a **collection of templates** for invoices and letters. While there are many tools and templates out there, I found it difficult to find a _simple template_ that I could _easily modify_ to my needs. The goal of this project is to provide a simple template that can be easily modified to suit also your needs.

## Invoice and Letter Template

**Features:**

- [x] Invoice Template
- [ ] Letter Template
- [ ] Support for multiple languages
- [ ] Support for multiple currencies
- [x] Type validation using [pydantic](https://docs.pydantic.dev)
- [x] QR Code generation for bank transfer using [qrbill](https://ctan.org/pkg/qrbill)
- [ ] Support `VAT > 0` (currently only `VAT = 0` is supported)
- [ ] Support multiple pages for invoices
- [x] Easy interaction using [just](https://just.systems/man/en/)
- [x] Using a `texlive/texlive:latest-full` container for building the templates
- [x] Python dependency management using [poetry](https://python-poetry.org)
- [x] Keep track of the amount of invoices (using a `sqlite` database)

_An example of the invoice template can be found [here](data/invoices/example.pdf)._

## Getting Started

> :warning: You will need to have [podman](https://podman.io) installed on your system[^1]

You can either just clone this repository or create a fork of it. First of all, you need to install the dependencies using **[poetry](https://python-poetry.org)** (if you haven't heard of it, you should google it, and follow a tutorial on how to use it). Additionally I suggest using **[just](https://just.systems/man/en/)**.

After you have installed the dependencies, you will have to customize the configuration files. The first file contains your personal information, and some settings for the template (an example file is located at [config.example.toml](config.example.toml)). Please create a copy of the file and name it `config.toml`. The second file contains the information about you customers (an example file is located at [data/customers.example.yml](data/customers.example.toml)). Please create a copy of the file and name it `data/customers.yml`. Lastly, you will have to create a file for each invoice you want to create (an example file is located at [data/invoices/example.yml](data/invoices/example.toml)). Please create a copy of the file and name it `data/invoices/<invoice-name>.yml`.

Following, you should be able to create your first invoice by running the following command:

```bash
just invoice <invoice-path>
```

You can view all available commands by running `just --list` (or just `just`).

[^1]: I dont currently support docker, but it should be easy to add it. Just open an issue if you need it.

## License

This project is licensed under the GNU GPLv3 License - see the [COPYING](COPYING) file for details.

_The invoice template is inspired by a template from [Selfnet e.V.](https://www.selfnet.de/)._
