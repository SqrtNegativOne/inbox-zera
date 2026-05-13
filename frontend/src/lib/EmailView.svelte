<script>
  /** @type {{ email: object, labels: Array, onLabel: (id: string) => void }} */
  let { email, labels, onLabel } = $props()

  let iframeEl = $state(null)

  function resizeIframe() {
    if (!iframeEl) return
    try {
      const doc = iframeEl.contentDocument || iframeEl.contentWindow?.document
      if (doc) {
        iframeEl.style.height = doc.documentElement.scrollHeight + 'px'
      }
    } catch {
      // cross-origin fallback — srcdoc is same-origin so this rarely fires
      iframeEl.style.height = '520px'
    }
  }
</script>

<article>
  <header>
    <span class="from">{email.from}</span>
    <h1 class="subject">{email.subject}</h1>
    <span class="date">{email.date}</span>
  </header>

  <div class="divider"></div>

  <div class="body">
    {#if email.is_html}
      <iframe
        bind:this={iframeEl}
        srcdoc={email.body}
        title="email content"
        sandbox="allow-popups allow-popups-to-escape-sandbox"
        onload={resizeIframe}
        scrolling="no"
      ></iframe>
    {:else}
      <pre>{email.body}</pre>
    {/if}
  </div>

  <footer>
    {#each labels as label, i}
      <button
        class="label-btn"
        onclick={() => onLabel(label.id)}
        title={`Press ${i + 1} to apply`}
      >
        {label.name}
      </button>
    {/each}
  </footer>
</article>

<style>
  article {
    width: min(660px, 100vw - 48px);
    padding: 52px 0 40px;
  }

  header {
    margin-bottom: 28px;
  }

  .from {
    display: block;
    font-family: 'Inter', system-ui, sans-serif;
    font-size: 0.78rem;
    font-weight: 400;
    color: #8a8078;
    letter-spacing: 0.02em;
    margin-bottom: 10px;
  }

  .subject {
    margin: 0 0 10px;
    font-family: 'Lora', Georgia, serif;
    font-size: 1.45rem;
    font-weight: 500;
    color: #1c1c1c;
    line-height: 1.3;
  }

  .date {
    display: block;
    font-family: 'Inter', system-ui, sans-serif;
    font-size: 0.72rem;
    font-weight: 300;
    color: #a89e92;
    letter-spacing: 0.04em;
  }

  .divider {
    height: 1px;
    background: #ddd6ca;
    margin-bottom: 32px;
  }

  .body {
    margin-bottom: 52px;
  }

  pre {
    margin: 0;
    font-family: 'Lora', Georgia, serif;
    font-size: 0.97rem;
    line-height: 1.8;
    color: #2e2a25;
    white-space: pre-wrap;
    word-break: break-word;
  }

  iframe {
    border: none;
    width: 100%;
    min-height: 120px;
    display: block;
    font-family: 'Lora', Georgia, serif;
  }

  footer {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
  }

  .label-btn {
    padding: 6px 18px;
    border: none;
    border-radius: 20px;
    background: #cfd9cb;
    color: #3a4e38;
    font-family: 'Inter', system-ui, sans-serif;
    font-size: 0.78rem;
    font-weight: 400;
    letter-spacing: 0.04em;
    cursor: pointer;
    transition: background 180ms ease, transform 80ms ease;
  }

  .label-btn:hover {
    background: #bfcebb;
  }

  .label-btn:active {
    transform: scale(0.97);
  }
</style>
