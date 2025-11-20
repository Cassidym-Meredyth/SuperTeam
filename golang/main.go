package main

import (
	"encoding/json"
	"fmt"
	"log"
	"os"
	"time"

	"github.com/gorilla/websocket"
	"github.com/joho/godotenv"
)

type MetaData struct {
	MMSI      int64   `json:"MMSI"`
	ShipName  string  `json:"ShipName"`
	Latitude  float64 `json:"latitude"`
	Longitude float64 `json:"longitude"`
	TimeUTC   string  `json:"time_utc"`
}

type PositionReport struct {
	Sog float64 `json:"Sog"`
	Cog float64 `json:"Cog"`
}

type Message struct {
	PositionReport PositionReport `json:"PositionReport"`
}

type AISMessage struct {
	MessageType string   `json:"MessageType"`
	MetaData    MetaData `json:"MetaData"`
	Message     Message  `json:"Message"`
}

func main() {
	err := godotenv.Load()
	if err != nil {
		log.Fatal("Ошибка при загрузке .env файла: ", err)
	}
	apiKey := os.Getenv("API_KEY")
	if apiKey == "" {
		log.Fatal("Нет API_KEY в .env")
	}

	url := "wss://stream.aisstream.io/v0/stream"
	c, _, err := websocket.DefaultDialer.Dial(url, nil)
	if err != nil {
		log.Fatal("dial error:", err)
	}
	defer c.Close()

	// Подписка на несколько активных морских областей
	sub := map[string]interface{}{
		"APIKey": apiKey,
		"BoundingBoxes": []interface{}{
			// Чёрное море
			[]interface{}{
				[]float64{60.0, 32.0},
				[]float64{80.0, 200.0},
			},
		},
		"FilterMessageTypes": []string{"PositionReport"},
	}

	msg, _ := json.Marshal(sub)
	err = c.WriteMessage(websocket.TextMessage, msg)
	if err != nil {
		log.Fatal("send error:", err)
	}

	fmt.Println("🌊 Подключено к AIS Stream")
	fmt.Printf("📍 Области: Северный морской путь\n")

	shipCount := 0
	startTime := time.Now()
	uniqueShips := make(map[int64]bool)

	ticker := time.NewTicker(30 * time.Second)
	defer ticker.Stop()

	go func() {
		for range ticker.C {
			elapsed := time.Since(startTime)
			fmt.Printf("\n📊 Получено %d сообщений от %d уникальных судов за %v\n\n",
				shipCount, len(uniqueShips), elapsed.Round(time.Second))
		}
	}()

	for {
		_, message, err := c.ReadMessage()
		if err != nil {
			log.Fatal("read error:", err)
		}

		var aisMsg AISMessage
		if err := json.Unmarshal(message, &aisMsg); err != nil {
			continue
		}

		if aisMsg.MessageType == "PositionReport" {
			shipCount++
			uniqueShips[aisMsg.MetaData.MMSI] = true

			// Определяем регион по координатам
			lat := aisMsg.MetaData.Latitude
			lon := aisMsg.MetaData.Longitude
			region := "Северный морской путь (СМП)"

			fmt.Printf("🚢 [%d] %s | %s | MMSI:%d | %.4f,%.4f | SOG:%.1f\n",
				shipCount,
				aisMsg.MetaData.ShipName,
				region,
				aisMsg.MetaData.MMSI,
				lat, lon,
				aisMsg.Message.PositionReport.Sog)
		}
	}
}
