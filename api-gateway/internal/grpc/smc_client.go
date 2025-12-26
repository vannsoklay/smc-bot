package grpc

import (
	"context"
	"time"

	smcpb "apigateway/proto/smcpb"

	"google.golang.org/grpc"
)

type SMCClient struct {
	client smcpb.SMCServiceClient
}

func NewSMCClient(addr string) (*SMCClient, error) {
	conn, err := grpc.Dial(addr, grpc.WithInsecure())
	if err != nil {
		return nil, err
	}

	return &SMCClient{
		client: smcpb.NewSMCServiceClient(conn),
	}, nil
}

// Analyze fetches signal from SMC service for a given symbol, timeframe, and exchange
func (s *SMCClient) Analyze(symbol, timeframe, exchange string) (*smcpb.AnalyzeResponse, error) {
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	return s.client.Analyze(ctx, &smcpb.AnalyzeRequest{
		Symbol:    symbol,
		Timeframe: timeframe,
		Exchange:  exchange,
	})
}
