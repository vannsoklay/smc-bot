package scheduler

import (
	"fmt"
	"log"
	"time"

	"apigateway/internal/domain"
	"apigateway/internal/grpc"
	"apigateway/internal/repo"
	telegram "apigateway/internal/repo"
)

type Scanner struct {
	client   *grpc.SMCClient
	store    *repo.MemoryStore
	telegram *telegram.Client
	pairs    []string
}

func NewScanner(client *grpc.SMCClient, store *repo.MemoryStore, tg *telegram.Client, pairs []string) *Scanner {
	return &Scanner{client, store, tg, pairs}
}

func (s *Scanner) Start() {
	go func() {
		ticker := time.NewTicker(2 * time.Minute)
		defer ticker.Stop()

		s.scan() // first scan immediately

		for range ticker.C {
			s.scan()
		}
	}()
}

func (s *Scanner) scan() {
	log.Println("🔍 Scanning market...")

	for _, pair := range s.pairs {
		resp, err := s.client.Analyze(pair, "15m", "binance")
		if err != nil || resp.Side == "" {
			continue
		}

		lastSignal, exists := s.store.Get(pair, "15m")
		newSignal := domain.Signal{
			Symbol:     resp.Symbol,
			Timeframe:  resp.Timeframe,
			Side:       resp.Side,
			EntryLow:   resp.EntryLow,
			EntryHigh:  resp.EntryHigh,
			StopLoss:   resp.StopLoss,
			TakeProfit: resp.TakeProfit,
		}

		// Send notification if:
		// 1. No previous signal exists (new signal)
		// 2. Signal has changed (different side or entry levels)
		shouldNotify := !exists || s.signalChanged(lastSignal, newSignal)

		if shouldNotify {
			msg := s.formatSignalMessage(newSignal)
			if err := s.telegram.SendMessage(msg); err != nil {
				log.Printf("Failed to send Telegram message for %s: %v", pair, err)
			}
			log.Printf("✅ Signal sent for %s: %s", pair, newSignal.Side)
		}

		// Always update the stored signal
		s.store.Save(newSignal)
	}
}

// signalChanged detects if the signal has meaningfully changed
func (s *Scanner) signalChanged(lastSignal, newSignal domain.Signal) bool {
	// Check if side changed (BUY -> SELL or vice versa)
	if lastSignal.Side != newSignal.Side {
		return true
	}

	// Check if entry levels changed significantly (more than 0.01% threshold)
	entryMidLast := (lastSignal.EntryLow + lastSignal.EntryHigh) / 2
	entryMidNew := (newSignal.EntryLow + newSignal.EntryHigh) / 2

	if entryMidLast > 0 {
		percentChange := ((entryMidNew - entryMidLast) / entryMidLast) * 100
		if percentChange < -0.01 || percentChange > 0.01 {
			return true
		}
	}

	// Check if stop loss or take profit changed significantly
	if lastSignal.StopLoss != newSignal.StopLoss || lastSignal.TakeProfit != newSignal.TakeProfit {
		return true
	}

	return false
}

// formatSignalMessage creates a formatted Telegram message
func (s *Scanner) formatSignalMessage(signal domain.Signal) string {
	return fmt.Sprintf(
		"📊 SMC Alert!\nSymbol: %s\nTimeframe: %s\nSide: %s\nEntry: %.4f-%.4f\nSL: %.4f\nTP: %.4f",
		signal.Symbol,
		signal.Timeframe,
		signal.Side,
		signal.EntryLow,
		signal.EntryHigh,
		signal.StopLoss,
		signal.TakeProfit,
	)
}
