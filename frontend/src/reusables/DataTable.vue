<script setup lang="ts" generic="T extends object">
export interface Column {
  key: string
  label: string
  align?: 'left' | 'right'
}

defineProps<{ columns: Column[]; rows: T[]; rowKey: keyof T }>()

// Columns are addressed by string key, which a typed row object can't be indexed with
// directly. Narrowing here keeps callers free of index signatures on their models.
function cell(row: T, key: string): unknown {
  return (row as Record<string, unknown>)[key]
}
</script>

<template>
  <div class="overflow-x-auto">
    <table class="w-full text-sm">
      <thead>
        <tr class="border-b border-slate-200 dark:border-slate-700">
          <th
            v-for="column in columns"
            :key="column.key"
            :class="[
              'px-3 py-2 font-medium text-slate-500 dark:text-slate-400',
              column.align === 'right' ? 'text-right' : 'text-left',
            ]"
          >
            {{ column.label }}
          </th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="row in rows"
          :key="String(row[rowKey])"
          class="border-b border-slate-100 last:border-0 dark:border-slate-700/50"
        >
          <td
            v-for="column in columns"
            :key="column.key"
            :class="[
              'px-3 py-3 text-slate-900 dark:text-slate-100',
              column.align === 'right' ? 'text-right tabular-nums' : 'text-left',
            ]"
          >
            <slot :name="column.key" :row="row">{{ cell(row, column.key) }}</slot>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
