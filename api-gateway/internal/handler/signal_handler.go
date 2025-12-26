package handler

import (
	"net/http"

	"apigateway/internal/domain"
	"apigateway/internal/repo"

	"github.com/gin-gonic/gin"
)

func RegisterRoutes(r *gin.Engine, store *repo.MemoryStore) {

	// Return all signals
	// r.GET("/signals", func(c *gin.Context) {
	// 	signals := store.All() // All() returns []repo.Signal
	// 	c.JSON(http.StatusOK, signals)
	// })

	// Return signals for a specific symbol
	r.GET("/signals/:symbol", func(c *gin.Context) {
		symbol := c.Param("symbol")
		timeframe := c.Query("timeframe") // optional query param: ?timeframe=15m

		if timeframe != "" {
			if sig, ok := store.Get(symbol, timeframe); ok {
				c.JSON(http.StatusOK, sig)
				return
			}
			c.JSON(http.StatusOK, gin.H{"signal": nil})
			return
		}

		// If no timeframe is provided, return all signals for this symbol
		var results []domain.Signal
		for _, tf := range []string{"15m", "1h"} {
			if sig, ok := store.Get(symbol, tf); ok {
				results = append(results, sig)
			}
		}
		c.JSON(http.StatusOK, results)
	})
}
