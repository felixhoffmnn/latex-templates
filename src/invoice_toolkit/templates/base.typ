#import "@preview/letter-pro:3.0.0": letter-simple

#let letter-base(
  sender: (
    name: none,
    extra: none,
    street: none,
    zip: none,
    city: none,
    phone: none,
    email: none,
    website: none,
  ),
  tax: (
    office: none,
    number: none,
  ),
  bank: (
    name: none,
    iban: none,
    bic: none,
  ),
  recipient: (
    name: none,
    company: none,
    extra: none,
    street: none,
    zip: none,
    city: none,
  ),
  subject: none,
  date: none,
  reference-signs: (),
  information-box: (),
  body,
) = {
  if (
    sender.name == ""
      or sender.street == ""
      or sender.zip == ""
      or sender.city == ""
      or sender.phone == ""
      or sender.email == ""
  ) {
    panic("Sender information is incomplete. Please provide name, street, zip, city, phone, and email.")
  }
  if (
    recipient.name == "" or recipient.street == "" or recipient.zip == "" or recipient.city == ""
  ) {
    panic("Recipient information is incomplete. Please provide name, street, zip, and city.")
  }
  if subject == "" {
    panic("Subject is required.")
  }
  if (bank.name == "" or bank.iban == "" or bank.bic == "") {
    panic("Bank information is incomplete. Please provide name, iban, and bic.")
  }


  let recipient-text = {
    let parts = ()
    let company = recipient.at("company", default: "")
    let extra = recipient.at("extra", default: "")
    if company != "" { parts += ([#company],) }
    if company != "" {
      parts += ([z. Hd. #recipient.name],)
    } else {
      parts += ([#recipient.name],)
    }
    if extra != "" { parts += ([#extra],) }
    parts += ([#recipient.street],)
    parts += ([#recipient.zip #recipient.city],)
    parts.join(linebreak())
  }

  show: letter-simple.with(
    sender: (
      name: sender.name,
      address: sender.street + ", " + sender.zip + " " + sender.city,
      extra: [
        Telefon: #link("tel:" + sender.phone)[#sender.phone] \
        E-Mail: #link("mailto:" + sender.email)[#sender.email]
      ],
    ),

    recipient: recipient-text,

    information-box: context {
      if information-box != none {
        pad(right: 10mm, align(right)[
          #set text(size: 9pt)
          #grid(
            columns: (auto, auto),
            column-gutter: 8pt,
            row-gutter: 6pt,
            align: right,
            ..information-box,
          )
        ])
      }
    },
    reference-signs: reference-signs,

    date: if date != none { date } else { [#datetime.today().display("[day].[month].[year]")] },
    subject: subject,

    footer: [#text(size: 8pt)[
        #grid(
          columns: (auto, auto, auto, auto),
          column-gutter: 1fr,
          row-gutter: 3pt,
          inset: (top: 7pt),

          grid.hline(stroke: 0.75pt),

          [#sender.name \ #sender.street \ #sender.zip #sender.city],
          [#link("tel:" + sender.phone)[#sender.phone] \ #link("mailto:" + sender.email)[#sender.email] \ #link(
              sender.website,
            )[#sender.website]],
          [Finanzamt: #tax.office \ Steuernummer: #tax.number],
          [Bank: #bank.name \ IBAN: #bank.iban \ BIC: #bank.bic],
        )
      ]],

    margin: (
      left: 25mm,
      right: 20mm,
      top: 20mm,
      bottom: 40mm,
    ),
    font: ("Source Sans Pro", "Source Sans 3", "Arial", "Helvetica", "sans-serif"),
  )

  set text(lang: "de")
  body
}
