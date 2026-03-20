#import "base.typ": (
  letter-base, require-keys, validate-config, validate-recipient,
)

#let data = json(bytes(sys.inputs.at("data", default: bytes("{}"))))

#{
  assert(
    data != (:),
    message: "No data provided. Please provide data in JSON format.",
  )
  require-keys(data, ("config", "letter", "recipient", "content"), "data")
  validate-config(data.config)
  validate-recipient(data.recipient)
  require-keys(data.letter, ("subject", "opening", "closing"), "letter")
}

#let config = data.config
#let letter = data.letter
#let recipient = data.recipient
#let content = data.content

#let recipient-dict = {
  let d = (
    name: recipient.name,
    street: recipient.street,
    zip: recipient.zip,
    city: recipient.city,
  )
  if "company" in recipient and recipient.company != none {
    d.insert("company", recipient.company)
  }
  if "extra" in recipient and recipient.extra != none {
    d.insert("extra", recipient.extra)
  }
  d
}

#show: letter-base.with(
  sender: (
    name: config.sender.name,
    street: config.sender.street,
    zip: config.sender.zip,
    city: config.sender.city,
    phone: config.sender.phone,
    email: config.sender.email,
    website: config.sender.website,
  ),
  tax: (
    office: config.tax.office,
    number: config.tax.number,
  ),
  bank: (
    name: config.bank.name,
    iban: config.bank.iban,
    bic: config.bank.bic,
  ),
  recipient: recipient-dict,
  subject: letter.subject,
)

#letter.opening

// NOTE: content comes from the user's local Markdown file, converted to Typst
// markup by pypandoc.  #eval executes arbitrary Typst code — only process
// trusted input.
#eval(content, mode: "markup")

#letter.closing
#v(1cm)
#config.sender.name
