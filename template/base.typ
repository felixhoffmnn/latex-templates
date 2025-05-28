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
  recipient: (
    name: none,
    extra: none,
    street: none,
    zip: none,
    city: none,
  ),
  subject: none,
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


  let recipient-text = (
    if (recipient.at("extra", default: "") == "") {
      [
        #recipient.name \
        #recipient.street \
        #recipient.zip, #recipient.city
      ]
    } else {
      [
        #recipient.name \
        #recipient.extra \
        #recipient.street \
        #recipient.zip, #recipient.city
      ]
    }
  )

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
        pad(right: 10mm)[
          #grid(
            columns: (1fr, auto),
            gutter: 10pt,
            align: right,
            ..information-box,
          )
        ]
      }
    },
    reference-signs: reference-signs,

    date: [#datetime.today().display()],
    subject: subject,

    footer: [#text(size: 10pt)[
        #grid(
          columns: (1fr, 1fr, 1fr),
          gutter: 3pt,
          inset: (top: 7pt),

          grid.hline(stroke: 0.75pt),

          [#sender.name \ #sender.street \ #sender.zip, #sender.city],
          [#link("tel:" + sender.phone)[#sender.phone] \ #link("mailto:" + sender.email)[#sender.email] \ #link(
              sender.website,
            )[#sender.website]],
          [Finanzamt: #tax.office \ Steuernummer: #tax.number],
        )
      ]],

    margin: (
      left: 25mm,
      right: 20mm,
      top: 20mm,
      bottom: 40mm,
    ),
  )

  body
}
