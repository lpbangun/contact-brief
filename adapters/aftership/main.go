// Optional standalone adapter. No SMTP unless separately approved.
package main

import (
	"encoding/json"
	verifier "github.com/AfterShip/email-verifier"
	"io"
	"os"
	"time"
)

type request struct {
	Address        string  `json:"address"`
	Approved       bool    `json:"approved"`
	SMTP           bool    `json:"smtp"`
	SMTPApproved   bool    `json:"smtp_approved"`
	TimeoutSeconds float64 `json:"timeout_seconds"`
}
type response struct {
	Raw         *verifier.Result `json:"raw"`
	Error       string           `json:"error"`
	SMTPEnabled bool             `json:"smtp_enabled"`
}

func verify(req request) response {
	out := response{SMTPEnabled: req.SMTP}
	if !req.Approved || req.Address == "" || (req.SMTP && !req.SMTPApproved) {
		out.Error = "authorization_required"
		return out
	}
	if req.TimeoutSeconds <= 0 || req.TimeoutSeconds > 60 {
		out.Error = "invalid_timeout"
		return out
	}
	limit := time.Duration(req.TimeoutSeconds * float64(time.Second))
	v := verifier.NewVerifier().DisableSMTPCheck().DisableGravatarCheck().DisableDomainSuggest().ConnectTimeout(limit).OperationTimeout(limit)
	if req.SMTP {
		v.EnableSMTPCheck().EnableCatchAllCheck()
	}
	// Verify does not expose context cancellation. Main exits after the deadline,
	// terminating outstanding library goroutines; Python adds a process kill cap.
	done := make(chan response, 1)
	go func() {
		raw, err := v.Verify(req.Address)
		r := response{Raw: raw, SMTPEnabled: req.SMTP}
		if err != nil {
			r.Error = "verifier_error"
		}
		done <- r
	}()
	timer := time.NewTimer(limit)
	defer timer.Stop()
	select {
	case r := <-done:
		return r
	case <-timer.C:
		out.Error = "timeout"
		return out
	}
}
func main() {
	var req request
	dec := json.NewDecoder(io.LimitReader(os.Stdin, 16384))
	dec.DisallowUnknownFields()
	if err := dec.Decode(&req); err != nil {
		os.Exit(2)
	}
	if err := dec.Decode(new(any)); err != io.EOF {
		os.Exit(2)
	}
	if err := json.NewEncoder(os.Stdout).Encode(verify(req)); err != nil {
		os.Exit(2)
	}
}
