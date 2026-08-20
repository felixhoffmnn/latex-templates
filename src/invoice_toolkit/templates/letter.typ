#import "base.typ": letter-base

#let data = json(bytes(sys.inputs.at("data", default: bytes("{}"))))

#let config = data.config
#let letter = data.letter
#let recipient = data.recipient
#let content = data.content

#show: letter-base.with(
  sender: config.sender,
  tax: config.tax,
  bank: config.bank,
  recipient: recipient,
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
