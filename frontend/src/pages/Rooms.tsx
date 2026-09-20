import { createSignal, onMount } from 'solid-js'
import { For, Show } from 'solid-js'
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

export default function Rooms() {
  const [rows, setRows] = createSignal<Room[]>([])
  const [sheds, setSheds] = createSignal<Shed[]>([])
  const [form, setForm] = createSignal({ ...empty })
  const [editingId, setEditingId] = createSignal<number | null>(null)
  const [error, setError] = createSignal('')
  const isAdmin = getUser()?.role === 'admin'

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
    const id = editingId()
    try {
      if (id === null) {
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
      } else {
        await api(`/api/rooms/${id}`, {
          method: 'PATCH',
          body: JSON.stringify({
            roomCode: form().roomCode,
            species: form().species,
            capacityBags: Number(form().capacityBags),
            status: form().status,
          }),
        })
      }
      setForm({ ...empty })
      setEditingId(null)
      await load()
    } catch (err) {
      setError(err instanceof Error ? err.message : '保存失败')
    }
  }

  function startEdit(r: Room) {
    setEditingId(r.id)
    setForm({
      shedId: String(r.shedId),
      roomCode: r.roomCode,
      species: r.species,
      capacityBags: String(r.capacityBags),
      status: r.status,
    })
    setError('')
  }

  function cancelEdit() {
    setEditingId(null)
    setForm({ ...empty })
    setError('')
  }

  async function release(r: Room) {
    if (r.sealId == null) return
    const reason = window.prompt(
      `解除 ${r.roomCode} 的品种封印（${r.sealedSpecies}）\n请填写解封原因：`,
    )
    if (reason === null) return
    if (!reason.trim()) {
      setError('解封原因不能空白')
      return
    }
    setError('')
    try {
      await api(`/api/species-seals/${r.sealId}/release`, {
        method: 'POST',
        body: JSON.stringify({ reason: reason.trim() }),
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
        <p class="muted">菌种、袋数容量与房态；进入 fruiting 即封印品种，仅场长可解封</p>
      </header>
      {error() && <div class="error">{error()}</div>}

      <form class="panel form-grid" onSubmit={onSubmit}>
        <label>
          所属菇房
          <select
            value={form().shedId}
            onChange={(e) => setForm({ ...form(), shedId: e.currentTarget.value })}
            disabled={editingId() !== null}
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
          {editingId() === null ? '新增出菇室' : '保存修改'}
        </button>
        <Show when={editingId() !== null}>
          <button type="button" class="btn ghost" onClick={cancelEdit}>
            取消编辑
          </button>
        </Show>
      </form>

      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>ID</th>
              <th>菇房 ID</th>
              <th>编号</th>
              <th>品种</th>
              <th>封印物种</th>
              <th>容量</th>
              <th>状态</th>
              <th />
            </tr>
          </thead>
          <tbody>
            <For each={rows()}>
              {(r) => (
                <tr>
                  <td>{r.id}</td>
                  <td>{r.shedId}</td>
                  <td>{r.roomCode}</td>
                  <td>{r.species}</td>
                  <td>
                    <Show when={r.sealedSpecies} fallback={<span class="muted">—</span>}>
                      <span class="badge sealed" title={`封印 #${r.sealId}`}>
                        🔒 {r.sealedSpecies}
                      </span>
                    </Show>
                  </td>
                  <td>{r.capacityBags}</td>
                  <td>
                    <span class={statusBadge(r.status)}>{r.status}</span>
                  </td>
                  <td>
                    <button type="button" class="btn ghost" onClick={() => startEdit(r)}>
                      编辑
                    </button>
                    <Show when={isAdmin && r.sealId != null}>
                      <button type="button" class="btn ghost" onClick={() => release(r)}>
                        解封
                      </button>
                    </Show>
                    <button type="button" class="btn ghost" onClick={() => remove(r.id)}>
                      删除
                    </button>
                  </td>
                </tr>
              )}
            </For>
          </tbody>
        </table>
      </div>
    </div>
  )
}
