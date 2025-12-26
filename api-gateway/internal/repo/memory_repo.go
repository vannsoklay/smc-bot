package repo

import (
	"sync"

	"apigateway/internal/domain"
)

type MemoryStore struct {
	mu   sync.RWMutex
	data map[string]domain.Signal
}

func NewMemoryStore() *MemoryStore {
	return &MemoryStore{
		data: make(map[string]domain.Signal),
	}
}

// Save stores a signal using symbol+timeframe as key
func (s *MemoryStore) Save(sig domain.Signal) {
	s.mu.Lock()
	defer s.mu.Unlock()
	key := sig.Symbol + "_" + sig.Timeframe
	s.data[key] = sig
}

// Get retrieves the last signal
func (s *MemoryStore) Get(symbol, timeframe string) (domain.Signal, bool) {
	s.mu.RLock()
	defer s.mu.RUnlock()
	key := symbol + "_" + timeframe
	sig, ok := s.data[key]
	return sig, ok
}
