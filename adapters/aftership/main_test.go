package main

import (
	"context"
	"errors"
	"net"
	"testing"
)

func TestRealLibraryOffline(t *testing.T) {
	old := net.DefaultResolver
	defer func() { net.DefaultResolver = old }()
	calls := 0
	net.DefaultResolver = &net.Resolver{PreferGo: true, Dial: func(context.Context, string, string) (net.Conn, error) {
		calls++
		return nil, errors.New("blocked by offline test")
	}}
	r := verify(request{Address: "not-an-address", Approved: true, TimeoutSeconds: 1})
	if r.Raw == nil || r.Raw.Syntax.Valid || r.Error != "" || calls != 0 {
		t.Fatalf("invalid syntax result: %+v calls=%d", r, calls)
	}
	r = verify(request{Address: "fixture@example.invalid", Approved: true, SMTP: true, SMTPApproved: true, TimeoutSeconds: 1})
	if r.Error == "" || !r.SMTPEnabled || calls == 0 {
		t.Fatalf("DNS error must remain error: %+v", r)
	}
}
func TestApprovalFailsClosed(t *testing.T) {
	for _, req := range []request{{Address: "fixture@example.invalid"}, {Address: "fixture@example.invalid", Approved: true, SMTP: true}} {
		if r := verify(req); r.Error != "authorization_required" || r.Raw != nil {
			t.Fatalf("unguarded dispatch: %+v", r)
		}
	}
}
