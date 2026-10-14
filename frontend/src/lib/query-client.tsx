'use client';
import {QueryClient,QueryClientProvider} from '@tanstack/react-query';
import {useState} from 'react';
import {DisplayPreferencesProvider} from './display-preferences';
import {IconContext} from '@phosphor-icons/react';
export function QueryProvider({children}:{children:React.ReactNode}){const [client]=useState(()=>new QueryClient({defaultOptions:{queries:{retry:false,refetchOnWindowFocus:false}}}));return <IconContext.Provider value={{weight:'regular'}}><QueryClientProvider client={client}><DisplayPreferencesProvider>{children}</DisplayPreferencesProvider></QueryClientProvider></IconContext.Provider>}
