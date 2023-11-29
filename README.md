# Invoice and Letter Templates

> :warning: This project only supports **German** currently.

This project is intended to be a **collection of templates** for invoices and letters. While there are many tools and templates out there, I found it difficult to find a _simple template_ that I could _easily modify_ to my needs. The goal of this project is to provide a simple template that can be easily modified to suit also your needs.

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

_An example of the invoice template can be found [here](invoices/example.pdf)._

## License

This project is licensed under the GNU GPLv3 License - see the [COPYING](COPYING) file for details.

| File                                 | Source                                                                       |
| ------------------------------------ | ---------------------------------------------------------------------------- |
| [invoice.tex](templates/invoice.tex) | https://github.com/mathialo/simpleinvoice/blob/master/examples/norwegian.tex |
