package main

import (
	"log"

	"github.com/gin-gonic/gin"

	grpcclient "apigateway/internal/grpc"
	"apigateway/internal/handler"
	"apigateway/internal/repo"
	"apigateway/internal/scheduler"
)

func main() {
	smcClient, err := grpcclient.NewSMCClient("localhost:50051")
	if err != nil {
		log.Fatal(err)
	}

	memStore := repo.NewMemoryStore()
	tgClient := repo.NewClient("8260354429:AAF8xVrZuimJaxMbr43PtMZAAftwFKelXVE", "1912920643")

	scanner := scheduler.NewScanner(
		smcClient,
		memStore,
		tgClient,
		[]string{"BTCUSDT", "ETHUSDT", "BNBUSDT", "ZECUSDT", "XRPUSDT", "SOLUSDT"},
	)
	scanner.Start()

	gin.SetMode(gin.ReleaseMode)
	r := gin.Default()
	handler.RegisterRoutes(r, memStore)

	log.Println("🚀 Go Gateway running on :9000")
	r.Run(":9000")
}
