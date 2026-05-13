<script>
  import { onMount } from 'svelte'
  import EmailView from './lib/EmailView.svelte'
  import { fetchLabels, fetchNextEmail, classifyEmail } from './lib/api.js'

  /** @type {'loading' | 'ready' | 'empty' | 'error'} */
  let status = $state('loading')
  let email = $state(null)
  let labels = $state([])
  let errorMsg = $state('')
  let visible = $state(false)

  onMount(async () => {
    try {
      labels = await fetchLabels()
      await advance()
    } catch (err) {
      status = 'error'
      errorMsg = err.message
    }
  })

  async function advance() {
    visible = false
    await tick(80)  // let fade-out finish before swapping content
    status = 'loading'

    const next = await fetchNextEmail()
    if (!next) {
      status = 'empty'
      return
    }

    email = next
    status = 'ready'
    await tick(30)  // one frame before fade-in so transition is visible
    visible = true
  }

  async function onLabel(labelId) {
    if (status !== 'ready') return
    try {
      visible = false
      await tick(300)
      await classifyEmail(email.id, labelId)
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
    if (idx >= 0 && idx < labels.length) {
      onLabel(labels[idx].id)
    }
  }
</script>

<svelte:window onkeydown={onKeydown} />

<main>
  {#if status === 'error'}
    <p class="ghost error">{errorMsg}</p>
  {:else if status === 'empty'}
    <p class="ghost">inbox zero</p>
  {:else if status === 'ready' && email}
    <div class="wrapper" class:visible>
      <EmailView {email} {labels} {onLabel} />
    </div>
  {/if}
  <!-- status === 'loading' renders nothing — screen stays calm during transitions -->
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

  .error {
    color: #c07060;
  }
</style>
