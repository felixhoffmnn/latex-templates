#import "base.typ": letter-base
#import "@preview/tiaoma:0.3.0"

#let data = json(bytes(sys.inputs.at("data", default: bytes("{}"))))

#let currency(value, locale: "de") = {
  let v = float(value)
  let negative = v < 0
  if negative { v = -v }

  let int-part = calc.floor(v)
  let dec-part = calc.round(v - int-part, digits: 2)
  let dec-str = {
    let d = calc.round(dec-part * 100)
    let s = str(d)
    if d < 10 { "0" + s } else { s }
  }

  let int-str = str(int-part)

  if locale == "de" {
    // Insert thousands separators (dots)
    let digits = int-str.clusters()
    let len = digits.len()
    let result = ""
    for (i, d) in digits.enumerate() {
      if i > 0 and calc.rem(len - i, 3) == 0 {
        result += "."
      }
      result += d
    }
    if negative { "-" }
    result + "," + dec-str
  } else {
    if negative { "-" }
    int-str + "." + dec-str
  }
}

#let custom-gray = luma(90%)

#let config = data.config
#let invoice = data.invoice
#let recipient = data.recipient
#let additional = data.additional
#let has_vat = data.has_vat
#let vat_groups = data.vat_groups
#let display_total = float(data.display_total)

#show: letter-base.with(
  sender: config.sender,
  tax: config.tax,
  bank: config.bank,
  recipient: recipient,
  subject: "Rechnung " + invoice.invoice_number,
  date: [#invoice.date],
  information-box: {
    let entries = (
      [Rechnungsnummer:],
      [#invoice.invoice_number],
      [Rechnungsdatum:],
      [#invoice.date],
    )
    if "start_date" in invoice and invoice.start_date != none {
      if "end_date" in invoice and invoice.end_date != none {
        entries += (
          [Leistungszeitraum:],
          [#invoice.start_date -- #invoice.end_date],
        )
      }
    }
    entries += ([Kundennummer:], [#invoice.customer_id])
    entries
  },
)

Sehr geehrte Damen und Herren,

meine Leistungen stelle ich Ihnen wie folgt in Rechnung.

#[
  #set text(size: 10pt)
  #show table.cell.where(y: 0): strong
  #table(
    columns: if has_vat {
      (auto, 1fr, auto, auto, auto, auto, auto)
    } else {
      (auto, 1fr, auto, auto, auto, auto)
    },
    align: if has_vat {
      (center, left, right, left, right, right, right)
    } else {
      (center, left, right, left, right, right)
    },
    stroke: 0.75pt,
    inset: 7pt,

    ..if has_vat {
      (
        table.header(
          [Pos.],
          [Bezeichnung],
          [Menge],
          [Einheit],
          [Einzel €],
          [MwSt %],
          [Netto €],
        ),
      )
    } else {
      (
        table.header(
          [Pos.],
          [Bezeichnung],
          [Menge],
          [Einheit],
          [Einzel €],
          [Gesamt €],
        ),
      )
    },

    ..for (i, item) in invoice.items.enumerate() {
      let desc = if "description" in item and item.description != none {
        [ \ #text(10pt)[#item.description]]
      }
      if has_vat {
        (
          [#(i + 1)],
          [*#item.name*#desc],
          [#item.quantity],
          [#item.unit],
          [#currency(item.price) €],
          [#item.vat_rate %],
          [#currency(item.total) €],
        )
      } else {
        (
          [#(i + 1)],
          [*#item.name*#desc],
          [#item.quantity],
          [#item.unit],
          [#currency(item.price) €],
          [#currency(item.total) €],
        )
      }
    },

    ..if has_vat {
      let colspan = 6
      let rows = (
        table.cell(colspan: colspan, align: left, [Nettobetrag]),
        [#currency(float(invoice.total)) €],
      )
      for (rate, group) in vat_groups {
        let rate-int = int(rate)
        if rate-int > 0 {
          rows += (
            table.cell(colspan: colspan, align: left, [zzgl. #rate-int% MwSt auf
              #currency(group.basis) €]),
            [#currency(group.amount) €],
          )
        } else {
          rows += (
            table.cell(colspan: colspan, align: left, [Umsatzsteuerfreie
              Leistungen (§19 UStG)]),
            [0,00 €],
          )
        }
      }
      rows += (
        table.cell(
          colspan: colspan,
          align: left,
          fill: custom-gray,
          [*Gesamtbetrag*],
        ),
        table.cell(fill: custom-gray, [*#currency(float(invoice.total_gross))
        €*]),
      )
      rows
    } else {
      (
        table.footer(
          table.cell(
            colspan: 5,
            align: left,
            fill: custom-gray,
            [*Gesamtbetrag\**],
          ),
          table.cell(fill: custom-gray, [*#currency(float(invoice.total)) €*]),
        ),
      )
    },
  )
  #if not has_vat [
    #text(size: 10pt)[\* Umsatzsteuerfreie Leistungen gemäß §19 UStG.]
  ]
]
#v(1em)

#block(breakable: false)[
  Bitte überweisen Sie den Betrag von *#currency(display_total) €* bis zum
  *#invoice.due_date* an die folgende Bankverbindung. _Der dargestellte QR-Code
  kann zur automatischen Übernahme der Daten in Ihr Online-Banking genutzt
  werden._

  #v(1em)
  #let billing-details = (
    [#grid(
      columns: (auto, 1fr),
      gutter: 10pt,

      [Kontoinhaber:], [#config.sender.name],
      [Bank:], [#config.bank.name],
      [IBAN:], [#config.bank.iban],
      [Betrag:], [#currency(display_total) €],
      [Verwendungszweck:], [#additional.purpose],
    )]
  )

  // https://de.wikipedia.org/wiki/EPC-QR-Code
  #let invoice-data = (
    "BCD
002
1
SCT

"
      + config.sender.name
      + "
"
      + config.bank.iban
      + "
EUR"
      + currency(display_total, locale: "en")
      + "


"
      + additional.purpose
  )

  #grid(
    columns: (3fr, 1fr),
    gutter: 3pt,

    grid.cell(align: left + horizon, billing-details),
    grid.cell(align: right + horizon, [#tiaoma.qrcode(invoice-data)]),
  )
  #v(1em)

  Vielen Dank für die gute Zusammenarbeit.
]
