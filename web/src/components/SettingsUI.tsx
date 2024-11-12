'use client'

import { useMutation } from '@tanstack/react-query'
import React, { useEffect } from 'react'
import { Input } from './ui/input'
import { Label } from './ui/label'
import { useToast } from './ui/use-toast'
import { Button } from './ui/button'
import { Config } from '@/lib/types'
import { useQuery } from '@tanstack/react-query'
import { Card, CardContent, CardHeader, CardTitle } from './ui/card'

function SettingsUI() {
    const [settings, setSettings] = React.useState<Config['credentials']>({
        civitai: { apikey: '' },
        huggingface: { token: '' }  // Устанавливаем начальное значение
    })

    const getSettingsQuery = useQuery({
        queryKey: ['settings'],
        queryFn: async () => {
            const resp = await fetch('/api/get_config')
            const data = await resp.json() as Config
            // Убедимся, что у нас есть все необходимые поля
            return {
                ...data,
                credentials: {
                    ...data.credentials,
                    huggingface: data.credentials.huggingface || { token: '' }
                }
            }
        }
    })

    useEffect(() => {
        if (getSettingsQuery.data?.credentials) {
            // Убедимся, что у нас есть объект huggingface
            const credentials = {
                ...getSettingsQuery.data.credentials,
                huggingface: getSettingsQuery.data.credentials.huggingface || { token: '' }
            }
            setSettings(credentials)
        }
    }, [getSettingsQuery.data])

    const { toast } = useToast()

    const setCredentialsMutation = useMutation({
        mutationFn: async (credentials: Config['credentials']) => {
            const response = await fetch(`/api/update_config`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ credentials }),
            })
            return response.json()
        },
        onSuccess: () => {
            toast({
                title: 'Settings saved successfully!'
            })
        }
    })

    if (getSettingsQuery.isLoading) {
        return <div className="p-8">Loading...</div>
    }

    return (
        <div className="flex flex-col p-10 space-y-6">
            {/* CivitAI Card */}
            <Card>
                <CardHeader>
                    <CardTitle>CivitAI Settings</CardTitle>
                </CardHeader>
                <CardContent>
                    <div className="flex flex-col space-y-2">
                        <Label htmlFor="civitai-key">CivitAI API Key</Label>
                        <Input
                            id="civitai-key"
                            type="password"
                            placeholder="Your CivitAI API key"
                            value={settings.civitai.apikey}
                            className="w-fit"
                            onChange={(e) => setSettings(prev => ({
                                ...prev,
                                civitai: { ...prev.civitai, apikey: e.target.value }
                            }))}
                        />
                        <p className="text-xs font-medium text-gray-600">
                            You can get your CivitAI API key from your{' '}
                            <a
                                href="https://civitai.com/user/account"
                                target="_blank"
                                rel="noreferrer"
                                className="text-blue-500 hover:text-blue-600"
                            >
                                CivitAI account settings page
                            </a>
                            .
                            <br />
                            Scroll to the bottom of the page to the section titled
                            "API Keys", and create one.
                            <br />
                            <br />
                            This key is saved locally and ONLY used to download
                            missing models directly from CivitAI. It is NEVER sent
                            anywhere else.
                        </p>
                    </div>
                </CardContent>
            </Card>

            {/* Hugging Face Card */}
            <Card>
                <CardHeader>
                    <CardTitle>Hugging Face Settings</CardTitle>
                </CardHeader>
                <CardContent>
                    <div className="flex flex-col space-y-2">
                        <Label htmlFor="hf-token">Access Token</Label>
                        <Input
                            id="hf-token"
                            type="password"
                            placeholder="Your Hugging Face access token"
                            value={settings.huggingface?.token || ''}
                            className="w-fit"
                            onChange={(e) => setSettings(prev => ({
                                ...prev,
                                huggingface: { token: e.target.value }
                            }))}
                        />
                        <p className="text-xs font-medium text-gray-600">
                            You can get your Hugging Face token from{' '}
                            <a
                                href="https://huggingface.co/settings/tokens"
                                target="_blank"
                                rel="noreferrer"
                                className="text-blue-500 hover:text-blue-600"
                            >
                                Hugging Face token settings
                            </a>
                            .
                            <br />
                            Create a new token with read access.
                            <br />
                            <br />
                            This token is saved locally and ONLY used to download
                            models from Hugging Face. It is NEVER sent anywhere else.
                        </p>
                    </div>
                </CardContent>
            </Card>

            {/* Save Button */}
            <div>
                <Button
                    onClick={() => setCredentialsMutation.mutate(settings)}
                    disabled={setCredentialsMutation.isPending}
                    variant="default"
                    className="mt-5"
                >
                    {setCredentialsMutation.isPending ? 'Saving...' : 'Save'}
                </Button>
            </div>
        </div>
    )
}

export default SettingsUI