---
제목: 의존성 주입(DI) 2편: 스프링은 무엇을 대신 해 주나
---

의존성 주입을 스프링 프레임워크에서 어떻게 활용하고 있는지 보자.

## 진행 버전
- Spring Boot 4.1 
- Kotlin 2.3 (JDK 25)

---

## 스프링 컨테이너가 대신 해 주는 것

**IoC(Inversion of Control) 제어의 역전**: 제어 흐름을 반전시키는 설계 원칙으로 개발자가 직접 제어하는 것이 아니라 프레임워크가 대신 제어하는 것을 의미한다. 

IoC라는 용어는 1988년 Ralph E. Johnson과 Brian Foote가 Journal of Object-Oriented Programming에 게재한 Designing Reusable Classes에서 처음 사용되었다고 한다. (개념 자체는 그 이전에도 있었다고 한다.)

[Designing Reusable Classes](https://www.laputan.org/drc/drc.html)
> One important characteristic of a framework is that the methods defined by the user to tailor the framework will often be called from within the framework itself, rather than from the user's application code. The framework often plays the role of the main program in coordinating and sequencing application activity. This inversion of control gives frameworks the power to serve as extensible skeletons. The methods supplied by the user tailor the generic algorithms defined in the framework for a particular application.
> 
> 프레임워크의 중요한 특징 중 하나는, 사용자가 프레임워크를 자기 용도에 맞추려고 정의한 메소드를 애플리케이션 코드가 아니라 프레임워크가 호출하는 경우가 많다는 것이다. 프레임워크는 흔히 메인 프로그램 역할을 맡아 애플리케이션의 동작을 조율하고 실행 순서를 정한다. 이 제어의 역전 덕분에 프레임워크는 확장 가능한 뼈대 역할을 할 수 있다. 사용자가 작성한 메소드는 프레임워크에 정의된 범용 알고리즘을 각 애플리케이션에 맞게 다듬는다.

**DI(Dependency Injection) 의존성 주입**: IoC를 구현하는 방법 중 하나로, 객체가 필요한 의존성을 외부에서 받는 방식이다. 

**DI 외 다른 IoC 구현 사례**
- 콜백
- 템플릿 메소드 패턴
- 옵저버 패턴 
- ... 등

```kotlin
// DI 사용하지 않을 시
@Service
class OrderFacadeService {
    // 개발자가 직접 생성하여 제어
    private val redisClient = RedisClient()
    private val lockExecutor = DistributedLockExecutor(redisClient)
    private val paymentClient = PaymentClient()
    private val orderRepository = OrderRepository()
    private val orderService = OrderService(orderRepository)
    ...
}

// DI 사용 시
@Service
class OrderFacadeService(
    // 스프링 컨테이너가 생성하여 주입
    private val lockExecutor: DistributedLockExecutor,
    private val paymentClient: PaymentClient,
    private val orderService: OrderService,
) {
    ...
}
```

스프링은 IoC 컨테이너를 사용하여 인스턴스 생성, 연결, 수명 주기, 스코프를 관리하고 생성자 주입(권장 방법. 세터, 필드 주입도 가능)을 통해 의존성 관리를 한다. DI 덕분에 로직 수정 없이 구현체 변경이 가능해지고 IoC 컨테이너 덕분에 생성 및 제어를 직접 할 필요가 없어진다.

## BeanFactory

```java
public interface BeanFactory {
    Object getBean(String name) throws BeansException;
    <T> T getBean(String name, Class<T> requiredType) throws BeansException;
    Object getBean(String name, @Nullable Object @Nullable ... args) throws BeansException;
    <T> T getBean(Class<T> requiredType) throws BeansException;
    <T> T getBean(Class<T> requiredType, @Nullable Object @Nullable ... args) throws BeansException;

    <T> ObjectProvider<T> getBeanProvider(Class<T> requiredType);
    <T> ObjectProvider<T> getBeanProvider(ResolvableType requiredType);
    <T> ObjectProvider<T> getBeanProvider(ParameterizedTypeReference<T> requiredType);

    boolean containsBean(String name);
    boolean isSingleton(String name) throws NoSuchBeanDefinitionException;
    boolean isPrototype(String name) throws NoSuchBeanDefinitionException;
    boolean isTypeMatch(String name, ResolvableType typeToMatch) throws NoSuchBeanDefinitionException;
    boolean isTypeMatch(String name, Class<?> typeToMatch) throws NoSuchBeanDefinitionException;

    @Nullable Class<?> getType(String name) throws NoSuchBeanDefinitionException;
    @Nullable Class<?> getType(String name, boolean allowFactoryBeanInit) throws NoSuchBeanDefinitionException;

    String[] getAliases(String name);
}

public class DefaultListableBeanFactory extends AbstractAutowireCapableBeanFactory
		implements ConfigurableListableBeanFactory, BeanDefinitionRegistry, Serializable {
    ...

    @Override
	public <T> T getBean(Class<T> requiredType) throws BeansException {
		return getBean(requiredType, (Object[]) null);
	}

	@SuppressWarnings("unchecked")
	@Override
	public <T> T getBean(Class<T> requiredType, @Nullable Object @Nullable ... args) throws BeansException {
		Assert.notNull(requiredType, "Required type must not be null");
		Object resolved = resolveBean(ResolvableType.forRawClass(requiredType), args, false);
		if (resolved == null) {
			throw new NoSuchBeanDefinitionException(requiredType);
		}
		return (T) resolved;
	}
    ...
}
```

## ApplicationContext



```java
public interface ApplicationContext extends EnvironmentCapable, ListableBeanFactory, HierarchicalBeanFactory,
		MessageSource, ApplicationEventPublisher, ResourcePatternResolver

public class GenericApplicationContext extends AbstractApplicationContext implements BeanDefinitionRegistry {

	private final DefaultListableBeanFactory beanFactory;
    	
	public GenericApplicationContext() {
		this.beanFactory = new DefaultListableBeanFactory();
	}

	public GenericApplicationContext(DefaultListableBeanFactory beanFactory) {
		Assert.notNull(beanFactory, "BeanFactory must not be null");
		this.beanFactory = beanFactory;
	}

    public GenericApplicationContext(@Nullable ApplicationContext parent) {
		this();
		setParent(parent);
	}

	public GenericApplicationContext(DefaultListableBeanFactory beanFactory, ApplicationContext parent) {
		this(beanFactory);
		setParent(parent);
	}

    @Override
	public void setApplicationStartup(ApplicationStartup applicationStartup) {
		super.setApplicationStartup(applicationStartup);
		this.beanFactory.setApplicationStartup(applicationStartup);
	}

    @Override
	public final ConfigurableListableBeanFactory getBeanFactory() {
		return this.beanFactory;
	}

    @Override
	public void registerBeanDefinition(String beanName, BeanDefinition beanDefinition)
			throws BeanDefinitionStoreException {

		this.beanFactory.registerBeanDefinition(beanName, beanDefinition);
	}

	@Override
	public void removeBeanDefinition(String beanName) throws NoSuchBeanDefinitionException {
		this.beanFactory.removeBeanDefinition(beanName);
	}

	@Override
	public BeanDefinition getBeanDefinition(String beanName) throws NoSuchBeanDefinitionException {
		return this.beanFactory.getBeanDefinition(beanName);
	}

    public <T> void registerBean(@Nullable String beanName, Class<T> beanClass,
			@Nullable Supplier<T> supplier, BeanDefinitionCustomizer... customizers) {

		ClassDerivedBeanDefinition beanDefinition = new ClassDerivedBeanDefinition(beanClass);
		if (supplier != null) {
			beanDefinition.setInstanceSupplier(supplier);
		}
		for (BeanDefinitionCustomizer customizer : customizers) {
			customizer.customize(beanDefinition);
		}

		String nameToUse = (beanName != null ? beanName : beanClass.getName());
		registerBeanDefinition(nameToUse, beanDefinition);
	}
}
```

```java
public abstract class AbstractApplicationContext extends DefaultResourceLoader
		implements ConfigurableApplicationContext {
	@Override
	public void refresh() throws BeansException, IllegalStateException {
		this.startupShutdownLock.lock();
		try {
			this.startupShutdownThread = Thread.currentThread();

			StartupStep contextRefresh = this.applicationStartup.start("spring.context.refresh");

			// Prepare this context for refreshing.
			prepareRefresh();

			// Tell the subclass to refresh the internal bean factory.
			ConfigurableListableBeanFactory beanFactory = obtainFreshBeanFactory();

			// Prepare the bean factory for use in this context.
			prepareBeanFactory(beanFactory);

			try {
				// Allows post-processing of the bean factory in context subclasses.
				postProcessBeanFactory(beanFactory);

				StartupStep beanPostProcess = this.applicationStartup.start("spring.context.beans.post-process");
				// Invoke factory processors registered as beans in the context.
				invokeBeanFactoryPostProcessors(beanFactory);
				// Register bean processors that intercept bean creation.
				registerBeanPostProcessors(beanFactory);
				beanPostProcess.end();

				// Initialize message source for this context.
				initMessageSource();

				// Initialize event multicaster for this context.
				initApplicationEventMulticaster();

				// Initialize other special beans in specific context subclasses.
				onRefresh();

				// Check for listener beans and register them.
				registerListeners();

				// Instantiate all remaining (non-lazy-init) singletons.
				finishBeanFactoryInitialization(beanFactory);

				// Last step: publish corresponding event.
				finishRefresh();
			}

			catch (RuntimeException | Error ex) {
				if (logger.isWarnEnabled()) {
					logger.warn("Exception encountered during context initialization - " +
							"cancelling refresh attempt: " + ex);
				}

				// Stop already started Lifecycle beans to avoid dangling resources.
				if (this.lifecycleProcessor != null && this.lifecycleProcessor.isRunning()) {
					try {
						this.lifecycleProcessor.stop();
					}
					catch (Throwable ex2) {
						logger.warn("Exception thrown from LifecycleProcessor on cancelled refresh", ex2);
					}
				}

				// Destroy already created singletons to avoid dangling resources.
				destroyBeans();

				// Reset 'active' flag.
				cancelRefresh(ex);

				// Propagate exception to caller.
				throw ex;
			}

			finally {
				contextRefresh.end();
			}
		}
		finally {
			this.startupShutdownThread = null;
			this.startupShutdownLock.unlock();
		}
	}
}
```


### 경량 IoC 컨테이너 직접 만들어 보기

- 핵심 흐름만: 설계도 모으기(`beanDefinitionMap`) → `getBean`으로 꺼낼 때 생성 → 생성자 인자를 재귀로 채우기 → 만든 빈은 `singletonObjects`에
- 이름은 스프링과 맞춘다 — 아래 소주제와 힙 덤프에서 같은 이름을 다시 만난다
- 하지 않는 것: 컴포넌트 스캔(클래스 목록을 직접 넘긴다), 스코프, 프록시, `@Qualifier`·`@Primary` → 아래 소주제와 2·3절에서 스프링이 어떻게 하는지 본다

### 무엇을 만들지 모으기: 컴포넌트 스캔 → BeanDefinition

### 만들고 주입하기: getBean → createBean → 생성자 인자 해석

### 감싸기: initializeBean → BeanPostProcessor

### 다 만든 빈은 singletonObjects로

---

## 같은 인터페이스의 구현이 여럿일 때

### 후보 찾기

### 후보가 여럿일 때 고르는 순서

### List·Map으로 전부 받기

---

## 힙에서 확인하기

### 설계도와 실물: beanDefinitionMap · singletonObjects

### 스프링이 기록해 둔 의존 관계: dependentBeanMap

### List로 받은 빈

### @Configuration 클래스도 프록시다

### @Transactional 빈은 객체가 둘이다


---

## 참고
- https://docs.spring.io/spring-framework/reference/core/beans/introduction.html
- https://medium.com/@vkekukh/why-they-ask-whats-the-difference-between-ioc-and-dependency-injection-9cb1101c0a41
- 
- 