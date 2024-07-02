# Configuration Files

Within this directory, you can finde some example configuration files. These files contain information, which is used to generate the invoice. The following sections will explain the different configuration files.

The first configuration file contains your personal information, and some settings for the template (an example file is located at [config.example.yml](config.example.yml)). Please create a copy of the file and name it `config.yml`[^1]. The second file contains the information about you customers (an example file is located at [customer.example.csv](customer.example.csv)). Please create a copy of the file and name it `customer.csv`[^2]. Lastly, you will have to create a file containing your invoices you want to create (an example file is located at [invoice.example.yml](invoice.example.yml)). Please create a copy of the file and name it `invoice.yml`[^2].

[^1]: I would suggest to place the file in the root directory of the repository.
[^2]: Because this file contains sensitive information, I would suggest to place it outside of the repository. You can specify the location of the file using the `INVOICE_PATH` environment variable. Alternatively, it will default to the `data` directory.
