import type { Metadata } from 'next';
import '@fontsource/plus-jakarta-sans/400.css';
import '@fontsource/plus-jakarta-sans/500.css';
import '@fontsource/plus-jakarta-sans/600.css';
import '@fontsource/plus-jakarta-sans/700.css';
import '@fontsource/jetbrains-mono/400.css';
import '@fontsource/jetbrains-mono/500.css';
import './globals.css';
import {QueryProvider} from '@/lib/query-client';
export const metadata:Metadata={title:'Yol · Car rental in Azerbaijan',description:'Compare rental cars in Azerbaijan, choose your dates, and review an itemized quote with your AI concierge.',icons:{icon:'/assets/concierge-emblem.webp'}};
export default function Layout({children}:{children:React.ReactNode}){return <html lang="en" suppressHydrationWarning><body><script dangerouslySetInnerHTML={{__html:`try{var t=localStorage.getItem('yol-theme');document.documentElement.dataset.theme=t==='dark'||t==='light'?t:(matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light')}catch{}`} }/><QueryProvider>{children}</QueryProvider></body></html>}
