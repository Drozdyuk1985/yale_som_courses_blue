import { useEffect, useState } from 'react'

const SAYINGS = [
  'A penny saved is a penny earned. — Franklin',
  'Price is what you pay. Value is what you get. — Buffett',
  'Compound interest is the eighth wonder of the world.',
  'The love of money is the root of all evil. — 1 Timothy 6:10',
  'Wealth gotten by vanity shall be diminished, but he that gathereth by labour shall increase. — Proverbs 13:11',
  'Zakat purifies wealth: a portion given is a portion redeemed.',
  'Every fiftieth year, a Jubilee — debts released, land returned. — Leviticus 25',
  'Weber: the Protestant ethic turned thrift into a calling.',
  'Aquinas asked not what a thing sells for, but what it is justly worth.',
  'Artha — the pursuit of prosperity — is one of the four aims of life.',
  'Right livelihood: earn in a way that harms no one. — the Eightfold Path',
  'Spend less than you earn. Invest the difference. Wait.',
  'Income buys your week. Wealth buys your decades.',
  'Diversify: no prophet predicts the market twice.',
  'The rich rule over the poor, and the borrower is slave to the lender. — Proverbs 22:7',
  'Live below your means and your means will grow.',
]

export function MoneyTicker() {
  const [index, setIndex] = useState(() => Math.floor(Math.random() * SAYINGS.length))
  const [visible, setVisible] = useState(true)

  useEffect(() => {
    const cycle = setInterval(() => {
      setVisible(false)
      setTimeout(() => {
        setIndex((i) => (i + 1) % SAYINGS.length)
        setVisible(true)
      }, 450)
    }, 9000)

    return () => clearInterval(cycle)
  }, [])

  return (
    <div className="ticker">
      <span className="ticker-coin">$</span>
      <p className={`ticker-text ${visible ? 'in' : 'out'}`}>{SAYINGS[index]}</p>
    </div>
  )
}
