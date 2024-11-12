import { Nav } from '@/components/Nav'
import SettingsUI from '@/components/SettingsUI'

export const dynamic = 'force-dynamic'

export default function SettingsPage() {
    return (
        <main className="flex min-h-screen flex-col bg-white">
            <div>
                <Nav />
            </div>
            <div className="container mx-auto px-4 py-8">
                <h1 className="text-2xl font-bold mb-6">Settings</h1>
                <div className="bg-white rounded-lg shadow">
                    <SettingsUI />
                </div>
            </div>
        </main>
    )
}