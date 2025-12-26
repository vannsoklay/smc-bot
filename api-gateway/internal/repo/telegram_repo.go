package repo

import (
	"fmt"
	"net/http"
	"net/url"
)

type Client struct {
	Token  string
	ChatID string
}

func NewClient(token, chatID string) *Client {
	return &Client{Token: token, ChatID: chatID}
}

func (c *Client) SendMessage(message string) error {
	apiURL := fmt.Sprintf("https://api.telegram.org/bot%s/sendMessage", c.Token)
	resp, err := http.PostForm(apiURL, url.Values{
		"chat_id": {c.ChatID},
		"text":    {message},
	})
	if err != nil {
		return err
	}
	defer resp.Body.Close()
	return nil
}
