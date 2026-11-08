import { SelectField } from '@/components/FormField'
import { useCallback, useState } from 'react'
import { Link } from 'react-router-dom'
import { ArrowRight } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Carousel, CarouselContent, CarouselItem, CarouselNext, CarouselPrevious, CarouselDots } from '@/components/ui/carousel'
import { ResourceState } from '@/components/ResourceState'
import { useResource } from '@/lib/use-resource'
import { catalogService } from './catalog-service'
import { ProductCard, ProductGrid } from './ProductCard'
import { sortOptions } from './catalog-options'

const sports = ['Football', 'Cricket', 'Basketball', 'Badminton', 'Fitness', 'Volleyball', 'Table Tennis']
const slides = [
  { title: 'Bring your best game.', text: 'From the first touch to the final whistle. Find your football essentials.', image: 'home-img-1.png', category: 'football' },
  { title: 'Own the crease.', text: 'Make every innings count with gear for practice and match day.', image: 'home-img-2.png', category: 'cricket' },
  { title: 'Take your shot.', text: 'For the early starts, the extra reps and the love of the game.', image: 'home-img-3.png', category: 'basketball' },
]

export function HomePage() {
  const [ordering, setOrdering] = useState('-id')
  const featured = useResource('featured', useCallback((signal) => catalogService.products('featured=true', signal), []))
  const offers = useResource('offers', useCallback((signal) => catalogService.products('discounted=true&ordering=-discount_percent', signal), []))
  const latest = useResource(ordering, useCallback((signal) => catalogService.products(`ordering=${ordering}`, signal), [ordering]))
  return <div className="space-y-14">
    <Carousel opts={{ loop: true }} aria-label="SportHub highlights" className="pb-12">
      <CarouselContent>{slides.map((slide) => <CarouselItem key={slide.category}><section className="grid items-center gap-6 rounded-2xl bg-secondary p-8 sm:p-12 md:grid-cols-2"><div><p className="eyebrow">Every sport. Every player.</p><h1 className="my-5 max-w-md text-4xl font-extrabold leading-tight tracking-tight sm:text-6xl">{slide.title}</h1><p className="mb-7 max-w-md leading-7 text-muted-foreground">{slide.text}</p><Button asChild size="lg"><Link to={`/categories/${slide.category}`}>Explore {slide.category}<ArrowRight aria-hidden="true" /></Link></Button></div><img src={`/images/${slide.image}`} alt={`${slide.category} equipment`} className="mx-auto h-64 w-full object-contain sm:h-80" /></section></CarouselItem>)}</CarouselContent>
      <CarouselDots /><CarouselPrevious className="bottom-0 left-auto right-11 top-auto translate-y-0" /><CarouselNext className="bottom-0 right-0 top-auto translate-y-0" />
    </Carousel>
    <section aria-labelledby="sports-title"><h2 id="sports-title" className="mb-6 text-2xl font-bold">Shop by sport</h2><div className="grid grid-cols-2 gap-3 sm:grid-cols-4 lg:grid-cols-7">{sports.map((sport, i) => <Link to={`/categories/${sport.toLowerCase().replaceAll(' ', '-')}`} key={sport} className="flex flex-col items-center gap-3 rounded-xl border bg-card p-5 text-center text-sm font-semibold transition-colors hover:bg-secondary"><img src={`/images/icon-${i + 1}.png`} alt="" className="size-14 object-contain" />{sport}</Link>)}</div></section>
    <section><div className="mb-6 flex items-center justify-between"><h2 className="text-2xl font-bold">Special offers</h2><Link to="/shop?discounted=true&ordering=-discount_percent" className="text-sm text-primary">View offers →</Link></div><ResourceState {...offers} />
      {offers.data && (offers.data.results.length ? <Carousel opts={{ align: 'start' }} aria-label="Special offers" className="pb-12"><CarouselContent>{offers.data.results.slice(0, 10).map((product) => <CarouselItem key={product.id} className="sm:basis-1/2 lg:basis-1/4"><ProductCard product={product} /></CarouselItem>)}</CarouselContent><CarouselDots /><CarouselPrevious className="bottom-0 left-auto right-11 top-auto translate-y-0" /><CarouselNext className="bottom-0 right-0 top-auto translate-y-0" /></Carousel> : <p className="rounded-xl border border-dashed p-8 text-muted-foreground">No special offers right now. Check back soon.</p>)}
    </section>
    <section><h2 className="mb-6 text-2xl font-bold">Featured picks</h2><ResourceState {...featured} />{featured.data && <ProductGrid products={featured.data.results.slice(0, 6)} />}</section>
    <section><div className="mb-6 flex flex-wrap items-center justify-between gap-4"><h2 className="text-2xl font-bold">Latest gear</h2><SelectField label="Sort latest products" value={ordering} onChange={(event) => setOrdering(event.target.value)}>{sortOptions.map(([value, label]) => <option key={value} value={value}>{label}</option>)}</SelectField></div><ResourceState {...latest} />{latest.data && <ProductGrid products={latest.data.results.slice(0, 12)} />}<div className="mt-6 text-center"><Button asChild variant="outline"><Link to="/shop">Browse all products</Link></Button></div></section>
  </div>
}
