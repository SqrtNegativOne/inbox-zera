<script>
  import { onMount } from 'svelte'
  import EmailView from './lib/EmailView.svelte'
  import { fetchAccounts, fetchLabels, fetchNextEmail, classifyEmail } from './lib/api.js'

  /** @type {'loading' | 'ready' | 'empty' | 'error' | 'no-accounts'} */
  let status = $state('loading')
  let email = $state(null)
  let allLabels = $state([])
  let accountCount = $state(0)
  let errorMsg = $state('')
  let visible = $state(false)

  /** Labels belonging to the current email's account only. */
  let activeLabels = $derived(
    email ? allLabels.filter(l => l.account === email.account) : []
  )

  onMount(async () => {
    try {
      const accounts = await fetchAccounts()
      accountCount = accounts.length
      if (accountCount === 0) {
        status = 'no-accounts'
        return
      }
      allLabels = await fetchLabels()
      await advance()
    } catch (err) {
      status = 'error'
      errorMsg = err.message
    }
  })

  async function advance() {
    visible = false
    await tick(80)
    status = 'loading'

    const next = await fetchNextEmail()
    if (!next) {
      status = 'empty'
      return
    }

    email = next
    status = 'ready'
    await tick(30)
    visible = true
  }

  async function onLabel(labelId) {
    if (status !== 'ready') return
    try {
      visible = false
      await tick(300)
      await classifyEmail(email.id, labelId, email.account)
      await advance()
    } catch (err) {
      status = 'error'
      errorMsg = err.message
    }
  }

  function tick(ms) {
    return new Promise(r => setTimeout(r, ms))
  }

  function onKeydown(e) {
    if (status !== 'ready') return
    const idx = parseInt(e.key, 10) - 1
    if (idx >= 0 && idx < activeLabels.length) {
      onLabel(activeLabels[idx].id)
    }
  }
</script>

<svelte:window onkeydown={onKeydown} />

<main>
  {#if status === 'error'}
    <p class="ghost error">{errorMsg}</p>
  {:else if status === 'no-accounts'}
    <p class="ghost">no accounts — <code>POST /api/accounts</code> to authenticate</p>
  {:else if status === 'empty'}
    <p class="ghost">inbox zero</p>
  {:else if status === 'ready' && email}
    <div class="wrapper" class:visible>
      <EmailView {email} labels={activeLabels} {onLabel} multiAccount={accountCount > 1} />
    </div>
  {/if}
</main>

<style>
  main {
    min-height: 100vh;
    display: flex;
    align-items: flex-start;
    justify-content: center;
    padding: 0 24px;
  }

  .wrapper {
    opacity: 0;
    transition: opacity 280ms ease;
    width: 100%;
  }

  .wrapper.visible {
    opacity: 1;
  }

  .ghost {
    font-family: 'Inter', system-ui, sans-serif;
    font-size: 0.85rem;
    font-weight: 300;
    letter-spacing: 0.12em;
    color: #b0a89e;
    margin-top: 48vh;
    transform: translateY(-50%);
  }

  .ghost code {
    font-size: 0.8rem;
    background: #e8e2d8;
    padding: 2px 6px;
    border-radius: 4px;
    letter-spacing: 0;
  }

  .error {
    color: #c07060;
  }
</style>
