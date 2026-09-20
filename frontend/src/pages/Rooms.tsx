import { createSignal, onMount } from 'solid-js'
import { For } from 'solid-js'
import { api, getUser } from '../api/client'
import type { Room, RoomStatus, Shed } from '../types'

const statuses: RoomStatus[] = ['fruiting', 'idle', 'sanitize']

const empty = {
  shedId: '',
  roomCode: '',
  species: '',
  capacityBags: '',
  status: 'fruiting' as RoomStatus,
}

type EditDraft = { species: string; status: RoomStatus }

export default function Rooms() {
  const [rows, setRows] = createSignal<Room[]>([])
  const [sheds, setSheds] = createSignal<Shed[]>([])
  const [form, setForm] = createSignal({ ...empty })
  const [error, setError] = createSignal('')
  const [drafts, setDrafts] = createSignal<Record<number, EditDraft>>({})
  const [savingId, setSavingId] = createSignal<number | null>(null)

  const currentUser = getUser()
  const isAdmin = () => currentUser?.role === 'admin'

  async function load() {
    const [rooms, shedList] = await Promise.all([
      api<Room[]>('/api/rooms'),
      api<Shed[]>('/api/sheds'),
    ])
    setRows(rooms)
    setSheds(shedList)
  }

  onMount(() => {
    load().catch((e) => setError(e.message))
  })

  async function onSubmit(e: Event) {
    e.preventDefault()
    setError('')
    try {
      await api('/api/rooms', {
        method: 'POST',
        body: JSON.stringify({
          shedId: Number(form().shedId),
          roomCode: form().roomCode,
          species: form().species,
          capacityBags: Number(form().capacityBags),
          status: form().status,
        }),
      })
      setForm({ ...empty })
      await load()
    } catch (err) {
      setError(err instanceof Error ? err.message : '保存失败')
    }
  }

  function startEdit(r: Room) {
    setDrafts({ ...drafts(), [r.id]: { species: r.species, status: r.status } })
  }

  function cancelEdit(id: number) {
    const next = { ...drafts() }
    delete next[id]
    setDrafts(next)
  }

  function updateDraft(id: number, patch: Partial<EditDraft>) {
    const cur = drafts()[id]
    if (cur) setDrafts({ ...drafts(), [id]: { ...cur, ...patch } })
  }

  async function saveEdit(r: Room) {
    const draft = drafts()[r.id]
    if (!draft) return
    setError('')
    setSavingId(r.id)
    try {
      await api(`/api/rooms/${r.id}`, {
        method: 'PATCH',
        body: JSON.stringify({ species: draft.species, status: draft.status }),
      })
      cancelEdit(r.id)
      await load()
    } catch (err) {
      setError(err instanceof Error ? err.message : '保存失败')
    } finally {
      setSavingId(null)
    }
  }

  async function releaseSeal(r: Room) {
    if (!r.sealId) return
    const reason = (window.prompt(`解除「${r.sealedSpecies}」物种封印，请填写解封原因：`) || '').trim()
    if (!reason) {
      setError('解封原因不能空白')
      return
    }
    setError('')
    try {
      await api(`/api/species-seals/${r.sealId}/release`, {
        method: 'POST',
        body: JSON.stringify({ reason }),
      })
      await load()
    } catch (err) {
      setError(err instanceof Error ? err.message : '解封失败')
    }
  }

  async function remove(id: number) {
    if (!confirm('确认删除该出菇室？')) return
    try {
      await api(`/api/rooms/${id}`, { method: 'DELETE' })
      await load()
    } catch (err) {
      setError(err instanceof Error ? err.message : '删除失败')
    }
  }

  function statusBadge(status: RoomStatus) {
    return `badge ${status}`
  }

  return (
    <div>
      <header class="page-header">
        <h1>出菇室</h1>
        <p class="muted">
          菌种、袋数容量与房态；进入 fruiting 时按当时品种封印，封印未解除禁止改品种
          {isAdmin() ? '，场长可解封' : '，仅场长（admin）可解封'}
        </p>
      </header>
      {error() && <div class="error">{error()}</div>}

      <form class="panel form-grid" onSubmit={onSubmit}>
        <label>
          所属菇房
          <select
            value={form().shedId}
            onChange={(e) => setForm({ ...form(), shedId: e.currentTarget.value })}
            required
          >
            <option value="">选择菇房</option>
            <For each={sheds()}>
              {(s) => <option value={String(s.id)}>{s.name}</option>}
            </For>
          </select>
        </label>
        <label>
          室编号
          <input
            value={form().roomCode}
            onInput={(e) => setForm({ ...form(), roomCode: e.currentTarget.value })}
            required
          />
        </label>
        <label>
          品种
          <input
            value={form().species}
            onInput={(e) => setForm({ ...form(), species: e.currentTarget.value })}
            required
          />
        </label>
        <label>
          容量 (袋)
          <input
            type="number"
            min="1"
            value={form().capacityBags}
            onInput={(e) => setForm({ ...form(), capacityBags: e.currentTarget.value })}
            required
          />
        </label>
        <label>
          状态
          <select
            value={form().status}
            onChange={(e) =>
              setForm({ ...form(), status: e.currentTarget.value as RoomStatus })
            }
          >
            <For each={statuses}>{(s) => <option value={s}>{s}</option>}</For>
          </select>
        </label>
        <button type="submit" class="btn primary">
          新增出菇室
        </button>
      </form>

      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>ID</th>
              <th>菇房 ID</th>
              <th>编号</th>
              <th>品种</th>
              <th>封印品种</th>
              <th>容量</th>
              <th>状态</th>
              <th />
            </tr>
          </thead>
          <tbody>
            <For each={rows()}>
              {(r) => {
                const draft = () => drafts()[r.id]
                const sealed = () => r.sealId != null
                return (
                  <tr>
                    <td>{r.id}</td>
                    <td>{r.shedId}</td>
                    <td>{r.roomCode}</td>
                    <td>
                      {draft() ? (
                        <input
                          value={draft()!.species}
                          disabled={sealed()}
                          title={sealed() ? '物种封印未解除，禁止修改品种' : undefined}
                          onInput={(e) => updateDraft(r.id, { species: e.currentTarget.value })}
                        />
                      ) : (
                        r.species
                      )}
                    </td>
                    <td>
                      {sealed() ? (
                        <span class="seal-tag">🔒 {r.sealedSpecies}</span>
                      ) : (
                        <span class="muted">—</span>
                      )}
                    </td>
                    <td>{r.capacityBags}</td>
                    <td>
                      {draft() ? (
                        <select
                          value={draft()!.status}
                          onChange={(e) =>
                            updateDraft(r.id, { status: e.currentTarget.value as RoomStatus })
                          }
                        >
                          <For each={statuses}>{(s) => <option value={s}>{s}</option>}</For>
                        </select>
                      ) : (
                        <span class={statusBadge(r.status)}>{r.status}</span>
                      )}
                    </td>
                    <td class="row-actions">
                      {draft() ? (
                        <>
                          <button
                            type="button"
                            class="btn primary"
                            disabled={savingId() === r.id}
                            onClick={() => saveEdit(r)}
                          >
                            保存
                          </button>
                          <button type="button" class="btn ghost" onClick={() => cancelEdit(r.id)}>
                            取消
                          </button>
                        </>
                      ) : (
                        <>
                          <button type="button" class="btn ghost" onClick={() => startEdit(r)}>
                            编辑
                          </button>
                          {sealed() && isAdmin() && (
                            <button
                              type="button"
                              class="btn warn"
                              onClick={() => releaseSeal(r)}
                            >
                              解封
                            </button>
                          )}
                          <button type="button" class="btn ghost" onClick={() => remove(r.id)}>
                            删除
                          </button>
                        </>
                      )}
                    </td>
                  </tr>
                )
              }}
            </For>
          </tbody>
        </table>
      </div>
    </div>
  )
}
