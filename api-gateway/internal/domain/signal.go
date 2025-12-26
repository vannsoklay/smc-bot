package domain

type Signal struct {
	Symbol     string  `json:"symbol"`
	Timeframe  string  `json:"timeframe"`
	Side       string  `json:"side"`
	EntryLow   float64 `json:"entry_low"`
	EntryHigh  float64 `json:"entry_high"`
	StopLoss   float64 `json:"stop_loss"`
	TakeProfit float64 `json:"take_profit"`
}
