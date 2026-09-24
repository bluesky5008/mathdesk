import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState, type FormEvent } from 'react'

import { PageHeader } from '../components/PageHeader'
import { Button } from '../components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card'
import { Field } from '../components/ui/field'
import { Input } from '../components/ui/input'
import { fetchBrand, saveBrand, type Brand } from '../api'
import { AccountsSection } from './AccountsSection'
import { ClassMinutesSetting } from './ClassMinutesSetting'

const EMPTY: Brand = { campus_name: '', brand_colour: null, logo_data_url: null }

// 계정 관리는 원장에게만 보인다(서버도 원장 외에는 403)
export function SettingsPage({ account }: { account?: { currentUserId: number } } = {}) {
  const queryClient = useQueryClient()
  const brand = useQuery({ queryKey: ['brand'], queryFn: fetchBrand })
  // 편집 전에는 서버 값을 그대로 보여준다. effect로 폼을 덮어쓰면 응답이 늦게 올 때
  // 사용자가 입력 중이던 값이 지워진다.
  const [edited, setEdited] = useState<Brand | null>(null)
  const form = edited ?? brand.data ?? EMPTY
  const setForm = setEdited

  const save = useMutation({
    mutationFn: () => saveBrand(form),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ['brand'] }),
  })

  function submit(event: FormEvent) {
    event.preventDefault()
    save.mutate()
  }

  return (
    <section>
      <PageHeader title="학원 설정" />

      <Card className="max-w-2xl">
        <CardHeader>
          <CardTitle>브랜드</CardTitle>
          <CardDescription>
            학부모에게 보내는 리포트 카드에 반영됩니다. 웹 화면의 색은 각자 고르는 테마를 따르며
            이 설정과 무관합니다.
          </CardDescription>
        </CardHeader>
        <CardContent className="pt-4">
          <form className="flex flex-col gap-4" onSubmit={submit}>
            <Field label="학원명" htmlFor="brand-name">
              <Input
                id="brand-name"
                value={form.campus_name}
                onChange={(event) => setForm({ ...form, campus_name: event.target.value })}
              />
            </Field>

            <Field label="시그니처 색" htmlFor="brand-colour">
              <div className="flex items-center gap-3">
                <input
                  type="color"
                  aria-label="시그니처 색 고르기"
                  className="h-9 w-12 cursor-pointer rounded-md border bg-surface p-1"
                  value={form.brand_colour ?? '#1D4ED8'}
                  onChange={(event) => setForm({ ...form, brand_colour: event.target.value })}
                />
                <Input
                  id="brand-colour"
                  className="w-32 font-mono"
                  placeholder="#1D4ED8"
                  value={form.brand_colour ?? ''}
                  onChange={(event) =>
                    setForm({ ...form, brand_colour: event.target.value || null })
                  }
                />
              </div>
            </Field>

            <p className="text-xs text-muted-fg">
              로고를 올리지 않으면 학원명 텍스트가 대신 표시됩니다.
            </p>

            <div className="flex items-center gap-3">
              <Button type="submit" disabled={save.isPending}>
                브랜드 저장
              </Button>
              {save.isSuccess && (
                <span role="status" className="text-sm text-success">
                  저장했습니다
                </span>
              )}
            </div>
            {save.isError && (
              <p role="alert" className="text-sm text-danger">
                {save.error.message}
              </p>
            )}
          </form>
        </CardContent>
      </Card>

      {account && <ClassMinutesSetting />}
      {account && <AccountsSection currentUserId={account.currentUserId} />}
    </section>
  )
}
