# Agent Memory API

## What it does
AIエージェントのセッション間記憶喪失を解決するメモリAPI。AES-256-GCM暗号化・削除証跡付きで日本語会話履歴を安全に保存・召喚する。

## Best for
- AIエージェントの長期記憶・複数呼び出しをまたいだ記憶管理
- 日本語会話コンテキストの永続管理
- 監査ログ付き記憶削除（GDPR・個人情報保護法対応）

## Do not use for
- カストディウォレットや暗号資産の管理
- 個人情報の永続的・長期的な保存（TTL設定推奨）
- バックアップシステムの代替

## Payment support
- USDC (Base mainnet)
- JPYC (Polygon)
- x402 protocol compatible
- HashPort compatible
- zERC-20 ready (planned)
