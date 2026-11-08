import { Link } from 'react-router-dom'
import { Star, StarHalf } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Carousel, CarouselContent, CarouselItem, CarouselNext, CarouselPrevious, CarouselDots } from '@/components/ui/carousel'

const testimonials = [
  { name: 'Ayush Shrestha', text: 'I ordered a football and a set of dumbbells from SportHub. The quality is excellent and delivery was super fast. Highly recommend for anyone looking for sports gear in Nepal!' },
  { name: 'Subika Maharjan', text: 'Finally, an online store in Nepal where I can buy quality cricket gear without worrying about fakes. The kit I ordered exceeded my expectations!' },
  { name: 'Anmol Shrestha', text: 'I was looking for home gym equipment and SportHub had everything I needed. The resistance bands and dumbbells are sturdy and delivered on time.' },
  { name: 'Khushi Pachhai', text: 'SportHub has a wide range of products. I got my badminton racket and shuttlecock set in perfect condition. The customer service team was very helpful with my queries.' },
]

export function AboutPage() {
  return <div className="space-y-14">
    <section className="grid items-center gap-10 md:grid-cols-2">
      <img src="/images/about-img.svg" alt="Getting ready for an active day" className="mx-auto w-full max-w-md" />
      <div className="space-y-5"><p className="eyebrow">Our mission</p><h1 className="page-title">Why choose SportHub?</h1><p className="leading-8 text-muted-foreground">At SportHub, we are passionate about sports and fitness. Our mission is to make high-quality sports equipment and gear accessible to athletes, students, and fitness enthusiasts across Nepal. From footballs and cricket kits to fitness accessories and protective gear, we provide products that help you perform at your best.</p><Button asChild><Link to="/contact">Contact us</Link></Button></div>
    </section>
    <section><h2 className="mb-6 text-2xl font-bold">Client testimonials</h2>
      <Carousel opts={{ align: 'start', loop: true }} aria-label="Client testimonials" className="pb-12">
        <CarouselContent>{testimonials.map((review, index) => <CarouselItem key={review.name} className="sm:basis-1/2 lg:basis-1/3"><figure className="page-panel flex h-full flex-col gap-5"><img src={`/images/pic-${index + 1}.png`} alt="" className="size-16 rounded-full object-cover" /><blockquote className="flex-1 leading-7 text-muted-foreground">{review.text}</blockquote><div className="flex gap-1 text-primary" aria-label="4.5 out of 5 stars">{[0, 1, 2, 3].map((star) => <Star key={star} aria-hidden="true" className="size-4 fill-current" />)}<StarHalf aria-hidden="true" className="size-4 fill-current" /></div><figcaption className="font-semibold">{review.name}</figcaption></figure></CarouselItem>)}</CarouselContent>
        <CarouselDots /><CarouselPrevious className="bottom-0 left-auto right-11 top-auto translate-y-0" /><CarouselNext className="bottom-0 right-0 top-auto translate-y-0" />
      </Carousel>
    </section>
  </div>
}
